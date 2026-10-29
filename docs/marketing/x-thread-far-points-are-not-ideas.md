# X thread — "The Gaps in the Map Are Not Ideas"

Manual thread (there is no X automation in this repo). Post it once the article is
live on the web (scheduled 2026-11-02; the cron lands it in the afternoon/evening UTC,
so check https://www.javieraguilar.ai/en/blog/far-points-are-not-ideas loads first).

Each tweet is kept under 280 characters (URLs count as 23) so it works on a free
account. There is nothing to edit: copy the blocks as they are.

## How to post it

This file lives on `main` once the article is published, and every tweet below is its
own fenced block, which GitHub renders with a copy button on mobile and desktop:

https://github.com/JaviMaligno/personal-website/blob/main/docs/marketing/x-thread-far-points-are-not-ideas.md

1. Open the original tweet, https://x.com/syntheticbeef/status/2112904858718367750,
   and **quote** it (Repost → Quote) with `1/`. That puts the thread in front of the
   people who saw the recipe and lets @syntheticbeef see the answer.
2. Post each of the rest as a reply to *your own* previous post, in order.

## Media

| Tweet | Attach |
|---|---|
| 1/ | The video (`~/Desktop/AGILabs-redes/videos/40-far-points-are-not-ideas.mp4`, also at `scripts/linkedin/posts/far-points-are-not-ideas-video-en/video.mp4`; 87 s, within the free 140 s limit). Without the video: `public/blog/far-points-are-not-ideas-linkedin.png` (the astronaut vs the far point). |
| 2/ | `public/blog/far-points-are-not-ideas-fig-1.png` (the hot-and-cold loop) |
| 4/ | `public/blog/far-points-are-not-ideas-fig-2.png` (the causal test) |
| 6/ | `public/blog/far-points-are-not-ideas-fig-3.png` (the 2D search) |
| 7/ | `public/blog/far-points-are-not-ideas-fig-4.png` (the cap) |
| 9/ | `public/blog/far-points-are-not-ideas-fig-5.png` (PLAIN vs PLAIND diversity) |

On a phone, the images open from `https://www.javieraguilar.ai/blog/<file>.png` once the
article is live: long-press → save.

---

**1/** (quote of @syntheticbeef's tweet)

```
I tested this on Steam games, arXiv papers and patents.

The catch: a point far from every game is also far from every text. No coherent description lives there.

What comes back is an ordinary game that looks like its neighbours. 🧵
```

**2/**

```
A point is 1,024 numbers. No LLM can read it, so first you have to decode it.

The obvious way: show the model the 8 nearest games, score its listing by cosine to the point, and let it play hot and cold for a few rounds.
```

**3/**

```
Hidden real games come back fine: with Star Farmer hidden, it wrote a space-farming game at cosine 0.87.

Far points don't. Neighbours: a black cat, some hamsters, My Furry Stepmom. Out came a kitten pushing blocks home. Cosine to the point: 0.069.
```

**4/**

```
Is the point doing anything, or only the neighbours?

Causal test: same point, same score, swap only the neighbours shown. In 12 of 12 combinations the listing follows the neighbours.

Hot and cold alone adds 0.04–0.07. It's "make a game from these 8".
```

**5/**

```
So the real test is a search with no neighbours: a GPU search maximises the cosine directly, then Claude or Codex rewrite the word soup until two models accept it as coherent.

On arXiv, for 90% of far points nothing beats the nearest existing paper.
```

**6/**

```
On Steam it's closer: for 25% of points a coherent text lands above the nearest game (15% with an independent judge).

But at a cosine of 0.09–0.14. The point is at 1.

"Further out than any game" is not "at the point".
```

**7/**

```
Why: texts don't fill the space. They sit on a narrow cap of the sphere. Two Steam games: cosine 0.41. Two random directions: 0.

Far points fall outside the cap. Before looking, I predicted the nearest arXiv paper at 0.062. It was 0.058.
```

**8/**

```
What did produce novelty: no map at all, just "invent a new game". The judges rated it the most novel with all six generators.

Then I read them in a row. One model wrote 46 museums out of 50. New against the catalogue, but the same idea again and again.
```

**9/**

```
The fix: let the model see the titles it already proposed. Repetition drops to the level of the guided arms, and novelty stays the highest on Steam, arXiv and patents.

Novelty came from asking for it, not from empty geometry.
```

**10/**

```
A point far from everything isn't an idea waiting to be written down. Almost always, it's a place where no text fits.

https://www.javieraguilar.ai/en/blog/far-points-are-not-ideas

Code, pre-registrations and Lean proofs: https://github.com/JaviMaligno/latent-gap-ideas
```
