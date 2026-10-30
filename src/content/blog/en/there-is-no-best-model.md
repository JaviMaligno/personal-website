---
title: "There Is No Best Model, Only a Frontier"
description: "No model wins on cost, quality and speed at once: there is a frontier of models that don't lose on everything to another one. How to read it, why to measure it per task and not per token, how to treat quality as a gate, and how it led me not to switch to a faster model."
pubDate: 2026-11-29
tags: ["AI", "LLM", "Economics", "Evaluation", "Engineering"]
lang: en
translationKey: there-is-no-best-model
heroImage: "/blog/there-is-no-best-model.png"
---

<style>
.ptf-fig { margin: 2rem 0; }
.ptf-fig svg { width: 100%; height: auto; display: block; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; }
.ptf-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.6rem; line-height: 1.5; }
</style>

A few weeks ago I tried a newer model in the [Industry Classifier](/en/projects/compliance-classifier), the agent that finds a company on the web, checks it is the right one and assigns it an industry code. The service runs on `gpt-6-luna`. The candidate was `gpt-6.1-terra`, released a few days earlier.

The result, in one line: **terra was clearly faster, more expensive, and I couldn't see any difference in quality.** Is it the better model? The honest answer is that the question is badly posed. It depends on what my service pays for, and the useful way to think about that has a name: the Pareto frontier.

## The idea in one picture

Choosing a model means trading at least three things: how good the answers are, how much they cost and how long they take. Rarely does one model win on all three.

A model **dominates** another when it is at least as good on every axis and strictly better on one: same quality and cheaper, or better and no slower. A dominated model can be discarded without any debate, because there is always a better option for any priority you might have. The models nobody dominates form the **Pareto frontier**.

<figure class="ptf-fig">
<svg viewBox="0 0 600 340" role="img" aria-label="Quality against cost per task. Four models form the frontier, drawn as a staircase that rises steeply at first and flattens at the top. Everything below and to the right of the staircase is the dominated region; two dominated models sit inside it, each beaten on both cost and quality by a frontier model.">
  <g font-family="system-ui,-apple-system,sans-serif">
    <path d="M110,290 L110,250 L220,250 L220,150 L330,150 L330,108 L500,108 L500,92 L570,92 L570,290 Z" fill="rgba(148,163,184,0.09)"/>
    <line x1="70" y1="290" x2="570" y2="290" stroke="#64748b" stroke-width="1.4"/>
    <line x1="70" y1="290" x2="70" y2="30" stroke="#64748b" stroke-width="1.4"/>
    <text x="320" y="322" text-anchor="middle" fill="#94a3b8" font-size="12">cost per task →</text>
    <text x="30" y="160" text-anchor="middle" fill="#94a3b8" font-size="12" transform="rotate(-90 30 160)">quality →</text>
    <path d="M110,290 L110,250 L220,250 L220,150 L330,150 L330,108 L500,108 L500,92 L570,92" stroke="#2dd4bf" stroke-width="2" fill="none"/>
    <circle cx="110" cy="250" r="7" fill="#2dd4bf"/>
    <circle cx="220" cy="150" r="7" fill="#2dd4bf"/>
    <circle cx="330" cy="108" r="7" fill="#2dd4bf"/>
    <circle cx="500" cy="92" r="7" fill="#2dd4bf"/>
    <text x="98" y="244" text-anchor="end" fill="#5eead4" font-size="12">small</text>
    <text x="208" y="146" text-anchor="end" fill="#5eead4" font-size="12">mid</text>
    <text x="318" y="104" text-anchor="end" fill="#5eead4" font-size="12">large</text>
    <text x="488" y="86" text-anchor="end" fill="#5eead4" font-size="12">flagship</text>
    <circle cx="300" cy="215" r="7" fill="none" stroke="#94a3b8" stroke-width="2"/>
    <circle cx="460" cy="165" r="7" fill="none" stroke="#94a3b8" stroke-width="2"/>
    <text x="300" y="240" text-anchor="middle" fill="#94a3b8" font-size="11.5">dominated</text>
    <text x="460" y="190" text-anchor="middle" fill="#94a3b8" font-size="11.5">dominated</text>
    <text x="470" y="275" text-anchor="middle" fill="#64748b" font-size="12" font-style="italic">dominated region</text>
    <text x="268" y="140" text-anchor="middle" fill="#94a3b8" font-size="11">knee</text>
    <circle cx="96" cy="44" r="5" fill="#2dd4bf"/>
    <text x="108" y="48" fill="#e2e8f0" font-size="11.5">frontier: nothing is both cheaper and better</text>
    <circle cx="96" cy="64" r="5" fill="none" stroke="#94a3b8" stroke-width="1.6"/>
    <text x="108" y="68" fill="#94a3b8" font-size="11.5">dominated: something is cheaper and better</text>
  </g>
</svg>
<figcaption>The frontier is the staircase: for each model on it, nothing is both cheaper and better. Everything in the shaded region is dominated and leaves the discussion. Along the frontier there is no technical winner, only a trade, and past the knee each extra unit of quality costs much more than the last.</figcaption>
</figure>

Two things follow from the picture.

The first is that the frontier settles a lot of arguments for free. If a model is dominated in your measurements, there is nothing to discuss.

The second is the opposite: **between two points on the frontier, no measurement decides.** Moving along it means buying one thing with another, and how much you are willing to pay is a business preference, not a technical fact. The engineering job is to draw the frontier honestly. The choice of point belongs to whoever knows what a second of waiting, a cent per task or a wrong answer costs.

There is also a shape worth looking for: the **knee**. Frontiers tend to rise steeply and then flatten. Past the knee, doubling the price buys a little more quality, and for many uses that little is not worth paying.

## Cost per task, not per token

The axis everyone looks at first is the price list: dollars per million input and output tokens. On that list, terra cost **ten times** more than luna. If I had drawn the frontier with it, the conversation would have ended there.

It isn't the cost I pay. What the service pays is the cost of **a classification**: around ten model calls, several web searches, page verification. I ran a short paired test, three real companies of a customer, two rounds each, both models interleaved and sharing the same web-search cache, so the evidence was the same for both. Measured per classification:

| | gpt-6-luna | gpt-6.1-terra |
|---|---:|---:|
| Price per token (relative) | 1× | 10× |
| Model cost per classification | \$0.0039 | \$0.0250 |
| Paid web searches per classification | 5.67 | 5.67 |
| **Total cost per classification** | **\$0.096** | **\$0.118** |
| Median time per classification | 82 s | 55 s |
| Correct primary code | 6 / 6 | 6 / 6 |

<figure class="ptf-fig">
<svg viewBox="0 0 600 320" role="img" aria-label="Terra relative to luna, in three steps. Price per token: ten times. Model cost per classification: 6.4 times, 0.025 against 0.0039 dollars, because terra uses fewer tokens. Total cost per classification: 1.23 times, 0.118 against 0.096 dollars, because the model is a small part of what a classification costs.">
  <g font-family="system-ui,-apple-system,sans-serif">
    <text x="100" y="34" text-anchor="middle" fill="#f8fafc" font-size="13.5" font-weight="600">Price per token</text>
    <line x1="20" y1="250" x2="180" y2="250" stroke="#64748b" stroke-width="1.2"/>
    <rect x="45" y="232" width="45" height="18" fill="#2dd4bf"/>
    <rect x="110" y="70" width="45" height="180" fill="#f59e0b"/>
    <text x="67.5" y="224" text-anchor="middle" fill="#5eead4" font-size="12">1×</text>
    <text x="132.5" y="62" text-anchor="middle" fill="#fbbf24" font-size="13" font-weight="600">10×</text>
    <text x="67.5" y="268" text-anchor="middle" fill="#94a3b8" font-size="12">luna</text>
    <text x="132.5" y="268" text-anchor="middle" fill="#94a3b8" font-size="12">terra</text>
    <text x="67.5" y="286" text-anchor="middle" fill="#94a3b8" font-size="11">$0.50/M</text>
    <text x="132.5" y="286" text-anchor="middle" fill="#94a3b8" font-size="11">$5/M</text>
    <text x="100" y="302" text-anchor="middle" fill="#64748b" font-size="10.5">output price</text>
    <text x="200" y="160" text-anchor="middle" fill="#64748b" font-size="20">→</text>
    <text x="300" y="34" text-anchor="middle" fill="#f8fafc" font-size="13.5" font-weight="600">Model cost / task</text>
    <line x1="220" y1="250" x2="380" y2="250" stroke="#64748b" stroke-width="1.2"/>
    <rect x="245" y="232" width="45" height="18" fill="#2dd4bf"/>
    <rect x="310" y="134.8" width="45" height="115.2" fill="#f59e0b"/>
    <text x="267.5" y="224" text-anchor="middle" fill="#5eead4" font-size="12">1×</text>
    <text x="332.5" y="126.8" text-anchor="middle" fill="#fbbf24" font-size="13" font-weight="600">6.4×</text>
    <text x="267.5" y="268" text-anchor="middle" fill="#94a3b8" font-size="12">luna</text>
    <text x="332.5" y="268" text-anchor="middle" fill="#94a3b8" font-size="12">terra</text>
    <text x="267.5" y="286" text-anchor="middle" fill="#94a3b8" font-size="11">$0.0039</text>
    <text x="332.5" y="286" text-anchor="middle" fill="#94a3b8" font-size="11">$0.025</text>
    <text x="400" y="160" text-anchor="middle" fill="#64748b" font-size="20">→</text>
    <text x="500" y="34" text-anchor="middle" fill="#f8fafc" font-size="13.5" font-weight="600">Total cost / task</text>
    <line x1="420" y1="250" x2="580" y2="250" stroke="#64748b" stroke-width="1.2"/>
    <rect x="445" y="232" width="45" height="18" fill="#2dd4bf"/>
    <rect x="510" y="227.9" width="45" height="22.1" fill="#f59e0b"/>
    <text x="467.5" y="224" text-anchor="middle" fill="#5eead4" font-size="12">1×</text>
    <text x="532.5" y="219.9" text-anchor="middle" fill="#fbbf24" font-size="13" font-weight="600">1.23×</text>
    <text x="467.5" y="268" text-anchor="middle" fill="#94a3b8" font-size="12">luna</text>
    <text x="532.5" y="268" text-anchor="middle" fill="#94a3b8" font-size="12">terra</text>
    <text x="467.5" y="286" text-anchor="middle" fill="#94a3b8" font-size="11">$0.096</text>
    <text x="532.5" y="286" text-anchor="middle" fill="#94a3b8" font-size="11">$0.118</text>
  </g>
</svg>
<figcaption>The same switch measured three ways. The multiplier shrinks from 10× to 6.4× once you count the tokens each model actually spends, and to 1.23× once you count everything else a classification pays for.</figcaption>
</figure>

Ten times per token became **23% more per task**, in two steps.

**From 10× to 6.4×: tokens.** Terra gets there in fewer turns (4.8 agent iterations per classification against 5.5) and thinks much less along the way: about a fifth of its output is reasoning, against half of luna's. It generates 1,362 output tokens per classification to luna's 2,540. So its model bill grew 6.4×, not 10×.

**From 6.4× to 1.23×: everything else.** With luna, the model is barely 4% of what a classification costs. The bulk is web search: both models made exactly the same paid searches, 5.67 per classification at \$0.016 each, about nine cents. A sixfold increase on four percent of the bill is a modest increase on the whole bill.

### What a search costs in tokens

The search fee isn't the whole cost of a search. Whatever the search returns, the model has to read, and the model charges for reading. About two thirds of what the agent reads in a classification is search and page material: the opening searches go in the first message and are sent again, whole, on every call (almost all of it from the cache), and each result of a search the agent launches itself travels in full in every following call until the next one.

Putting a price on one additional search, beyond its fee: if it costs the agent one more turn, that turn is roughly \$0.0003–0.0005 of tokens with luna and **\$0.003–0.004 with terra**. With luna, the search fee weighs 30 to 50 times more than reading the result. With terra, only four or five times more. The model's price multiplies the cost of everything it reads, so a more expensive model also makes its searches more expensive.

Here both models searched the same. That isn't guaranteed: when I [tested the previous swap in this service](/en/blog/the-new-model-is-cheaper), the new model searched about 12% more than the old one. A model's behaviour moves costs it doesn't bill itself, and a price list can't show that.

The general rule is the one I would put at the top of any model comparison: **draw the frontier with the cost and latency of the whole task in your system, not with the price list.** A model that is cheap per token and verbose can be expensive per task. One that is expensive per token and concise can be cheaper than it looks. And if the model is a small part of your cost, its price matters less than its effect on everything else.

## Three axes, and quality as a gate

The first picture has two axes, and the problem has three. You can draw all three, and doing it teaches something: with three axes almost nobody is dominated. A model needs only to be best at one thing, or at one combination, to survive. The more axes, the bigger the frontier and the less dominance discards on its own.

In practice, quality usually plays a different role from the other two. Before being a quantity to trade, it is a condition: the model has to be able to do the task. A classifier that gets half the codes wrong isn't a cheap option, it is no option at all. So the useful way to handle three axes is often a **gate**: fix a quality floor, discard what doesn't reach it, and draw the frontier between cost and latency with whatever passes.

My service has that gate written down. Before any change to the model or its harness, there are approved limits: among others, no stable regressions (cases the change fails in every round that the current version passed in every round) beyond what the control itself shows. In October I measured `gpt-6-luna` itself at three reasoning levels, on 38 cases of a benchmark picked on purpose to be hard: cases where the model had found the right company but got the code wrong or disagreed with the previous model. Four rounds each. On those cases the absolute accuracy is low by construction; what matters is the difference between levels:

<figure class="ptf-fig">
<svg viewBox="0 0 600 330" role="img" aria-label="The same model at three reasoning levels, cost relative to the default against median time. Low is 29 percent cheaper and 16 seconds faster, but gets 9 points fewer cases right, with two stable regressions, so it fails the quality gate. High is 16 percent more expensive and 11 seconds slower for the same accuracy within noise, so the default dominates it. The default is the only point left.">
  <g font-family="system-ui,-apple-system,sans-serif">
    <line x1="80" y1="290" x2="570" y2="290" stroke="#64748b" stroke-width="1.4"/>
    <line x1="80" y1="290" x2="80" y2="40" stroke="#64748b" stroke-width="1.4"/>
    <text x="325" y="322" text-anchor="middle" fill="#94a3b8" font-size="12">cost per classification, relative to default →</text>
    <text x="30" y="165" text-anchor="middle" fill="#94a3b8" font-size="12" transform="rotate(-90 30 165)">median time (s) →</text>
    <g fill="#94a3b8" font-size="11" text-anchor="middle">
      <text x="150" y="306">−30%</text><text x="360" y="306">default</text><text x="500" y="306">+20%</text>
    </g>
    <g fill="#94a3b8" font-size="11" text-anchor="end">
      <text x="72" y="234">40</text><text x="72" y="174">50</text><text x="72" y="114">60</text>
    </g>
    <g stroke="rgba(255,255,255,0.07)" stroke-width="1">
      <line x1="80" y1="230" x2="570" y2="230"/><line x1="80" y1="170" x2="570" y2="170"/><line x1="80" y1="110" x2="570" y2="110"/>
    </g>
    <circle cx="157" cy="242" r="12" fill="none" stroke="#f87171" stroke-width="2"/>
    <path d="M149,234 L165,250 M165,234 L149,250" stroke="#f87171" stroke-width="2"/>
    <text x="178" y="238" fill="#f87171" font-size="12.5" font-weight="600">low</text>
    <text x="178" y="254" fill="#94a3b8" font-size="11">−9 pts correct · 2 stable regressions</text>
    <text x="178" y="269" fill="#f87171" font-size="11">fails the quality gate</text>
    <circle cx="360" cy="146" r="9" fill="#2dd4bf"/>
    <text x="376" y="150" fill="#5eead4" font-size="12.5" font-weight="600">default</text>
    <text x="376" y="166" fill="#94a3b8" font-size="11">reference accuracy</text>
    <circle cx="472" cy="80" r="8" fill="none" stroke="#94a3b8" stroke-width="2"/>
    <text x="488" y="76" fill="#94a3b8" font-size="12.5" font-weight="600">high</text>
    <text x="488" y="92" fill="#94a3b8" font-size="11">−1 pt (noise)</text>
    <text x="488" y="107" fill="#94a3b8" font-size="11">dominated</text>
  </g>
</svg>
<figcaption>The same model, three settings, three different fates. Low is cheaper and faster but doesn't pass the gate. High passes it but the default is cheaper, faster and no worse. Only the default is left to choose. Accuracy is shown relative to the default: these 38 cases were picked because the model had failed or disagreed on them before, so the absolute rate says nothing about the service.</figcaption>
</figure>

`low` makes the agent stop researching: it runs 1.2 searches of its own per classification instead of 3.2, and many of its answers are abstentions without ever checking a page. It is 29% cheaper and 16 seconds faster, and it doesn't pass the gate. `high` passes the gate but buys nothing: +16% cost and +20% latency for the same accuracy within noise. The default dominates it. Two levels discarded, one by the gate and one by dominance, and no debate needed for either.

It also shows that a model isn't a single point on the map. Each reasoning level is a different point, and so is each prompt or harness you pair it with. What you place on the frontier are configurations, not model names. That multiplies the candidates, and it is one more reason to keep the gate and the per-task measurement cheap to run.

## Where the decision actually lives

Back to terra. On quality I saw no difference: both models got the right primary code in all six pairs. That doesn't prove they are equal. Six pairs on a bank where any recent model scores above 90% can't separate them. But both pass the gate, and above it the decision is between cost and latency: luna, cheaper and slower, and terra, faster and more expensive. Both on the frontier.

So the question becomes: is 27 seconds per classification worth 2.2 cents? Divide one by the other and you get the price of the trade: about **\$0.0008 per second saved, roughly \$3 per hour of waiting**. That is the slope of the line in the figure below. Terra wins if a second of waiting is worth more than that to someone. Luna wins otherwise.

<figure class="ptf-fig">
<svg viewBox="0 0 600 340" role="img" aria-label="Cost per classification against median time. Luna sits lower and to the right, terra higher and to the left. Three lines through luna represent different values of a second of waiting: at one dollar per hour terra lies above the line and loses, at about three dollars per hour the two tie, at twenty dollars per hour terra lies below and wins.">
  <g font-family="system-ui,-apple-system,sans-serif">
    <line x1="70" y1="300" x2="570" y2="300" stroke="#64748b" stroke-width="1.4"/>
    <line x1="70" y1="300" x2="70" y2="40" stroke="#64748b" stroke-width="1.4"/>
    <text x="320" y="330" text-anchor="middle" fill="#94a3b8" font-size="12">median time per classification (s) →</text>
    <text x="24" y="170" text-anchor="middle" fill="#94a3b8" font-size="12" transform="rotate(-90 24 170)">cost per classification →</text>
    <g fill="#94a3b8" font-size="11" text-anchor="middle">
      <text x="140" y="316">40</text><text x="280" y="316">60</text><text x="420" y="316">80</text><text x="560" y="316">100</text>
    </g>
    <g fill="#94a3b8" font-size="11" text-anchor="end">
      <text x="64" y="267">$0.08</text><text x="64" y="193">$0.10</text><text x="64" y="118">$0.12</text><text x="64" y="44">$0.14</text>
    </g>
    <line x1="70" y1="149.4" x2="560" y2="222" stroke="#64748b" stroke-width="1.4" stroke-dasharray="5 4"/>
    <line x1="70" y1="46" x2="560" y2="258" stroke="#94a3b8" stroke-width="1.4" stroke-dasharray="5 4"/>
    <line x1="378.6" y1="40" x2="466.8" y2="300" stroke="#64748b" stroke-width="1.4" stroke-dasharray="5 4"/>
    <rect x="76" y="128" width="62" height="16" fill="#1a1a24"/>
    <text x="80" y="140" fill="#94a3b8" font-size="11">$1 / h</text>
    <rect x="84" y="52" width="62" height="16" fill="#1a1a24"/>
    <text x="88" y="64" fill="#e2e8f0" font-size="11">$3 / h</text>
    <rect x="384" y="28" width="66" height="16" fill="#1a1a24"/>
    <text x="388" y="40" fill="#94a3b8" font-size="11">$20 / h</text>
    <circle cx="434" cy="203.4" r="8" fill="#2dd4bf"/>
    <circle cx="245" cy="121.7" r="8" fill="#f59e0b"/>
    <text x="420" y="234" text-anchor="end" fill="#5eead4" font-size="12.5" font-weight="600">luna</text>
    <text x="420" y="250" text-anchor="end" fill="#94a3b8" font-size="11">82 s · $0.096</text>
    <text x="196" y="104" fill="#fbbf24" font-size="12.5" font-weight="600">terra</text>
    <text x="196" y="88" fill="#94a3b8" font-size="11">55 s · $0.118</text>
  </g>
</svg>
<figcaption>Each dashed line joins the points that cost the same as luna once a second of waiting has a price. Below the line beats luna, above it loses. Terra sits exactly on the $3/hour line: whether it is the better model depends entirely on that number.</figcaption>
</figure>

Put that way, the decision stops being about models and becomes a question I can take to the people who use the service: is anyone waiting those 27 seconds, and what does that wait cost? In this case I decided to stop: 23% more per classification for no visible gain in quality, with latency as the only argument in favour. If one day the classification sits in an interactive flow where someone is waiting in front of the screen, the same numbers will give another answer, and I will only need to measure again.

## Three ways to balance the axes

What I did above is a mix of the three practical ways to decide along a frontier. They aren't exclusive.

- **Hard constraints, then optimise one axis.** Write down the limits first: quality no worse than the current model on your benchmark, p95 latency below X seconds, data stays in a given region. Among what survives, take the cheapest. It is the most robust option because it doesn't force you to put a price on everything, and it removes many points before any comparison. The quality gate of the previous section is one of these.
- **Put a price on what isn't money.** Turn latency and errors into dollars: what a second of waiting costs, what a wrong answer that reaches a person costs. Then minimise one number. It is what I did with the seconds. It forces you to make preferences explicit, which is uncomfortable and useful.
- **Don't choose a single point.** Route: the cheap model by default and the expensive one only for cases that need it (low confidence, hard inputs, a customer with stricter requirements). Your effective point then sits between the two, somewhere neither model reaches alone. The cost is complexity, and the router itself needs evaluating.

## Public benchmarks: for shortlisting, not deciding

There are public frontiers worth looking at. [Artificial Analysis](https://artificialanalysis.ai/models/comparisons) publishes, for each model, an aggregate intelligence index next to the price per million tokens, output speed, time to first token, end-to-end response time and, importantly, the **cost per index task** and the cost of running the whole index. That last metric is the right idea: it already accounts for one model writing twice as much as another to solve the same thing. [Arena](https://arena.ai) also offers a Pareto view of price against score, and for agents it plots score against cost per task.

They are useful for drawing a first map and discarding what is clearly dominated. They can't make your choice, for the same reason the price list couldn't make mine. Their tasks aren't yours. Their cost per task doesn't include your searches, your retries or your cache. In my service the model is under 5% of the cost; in a benchmark it is 100%. Use the public frontier to choose which three or four candidates are worth measuring, and draw yours with your own tasks.

## Self-hosted: another frontier, with fixed costs

The open-weight versus API question is another trade on the same axes, with two particularities.

On quality, the gap still exists, although it is smaller than it used to be. [Epoch AI](https://epoch.ai/data-insights/open-closed-eci-gap) measured in May 2026 that, since January, the best open-weight models trail the best closed ones by about **four months** on its aggregate capabilities index, around eight points. That is roughly the distance between GPT-5 and GPT-5.5. Epoch itself notes the figure probably understates the gap, because closed labs don't always release their best model. Four months doesn't sound like much, but on a saturated task like mine it may be irrelevant, and on a hard one it may decide whether you pass the gate.

On cost, the structure changes. An API charges per use: zero tasks, zero dollars. A GPU of your own charges per hour, whether you use it or not. Your cost per task is the hourly cost (machine, plus whoever operates it, updates it and wakes up when it fails) divided by the tasks you actually run per hour. With high, steady volume, that division can beat any API. With low volume it is terrible. As an illustration with round numbers: a GPU at one dollar an hour is over \$700 a month, and this whole service at around 500 classifications a month costs about \$50 per month with luna. At this volume the self-hosted point isn't even on the map.

And serving a model has its own frontier. Batching more requests per GPU lowers the cost per token but slows every user down: [SemiAnalysis's InferenceX](https://inferencex.semianalysis.com/glossary/pareto-frontier) maps exactly that trade between throughput per GPU and interactivity. Self-hosting doesn't escape the choice, it just adds another one.

Sometimes self-hosting isn't a point on the frontier but a constraint: data that can't leave your infrastructure. In that case it is another gate, one that removes the rest of the map, and the frontier you choose from is the one that's left.

## The frontier moves

What I like least about this exercise is also what makes it necessary: the frontier changes with every release. Terra came out days before I tested it. Luna came out weeks before that. The next model will move both points or add a third, and the answer from this month will need redoing.

That's why it's worth keeping the measurement cheap and repeatable rather than the conclusion fixed: a paired benchmark with your tasks, a quality gate written down before the first call, cost and latency measured per task, and the trade made explicit: how much a second is worth, how much an error is worth. With that, a new model is an afternoon of measurement and a line on a chart. Without it, it is a debate about the price list.

---

*The Industry Classifier is described in [its project page](/en/projects/compliance-classifier). How I test a model swap in it, and what that testing costs, is in [The New Model Is Cheaper. Testing It Isn't](/en/blog/the-new-model-is-cheaper).*
