---
title: "I Made a Product Demo Video Entirely with AI"
description: "How I used Claude Code to build a recording pipeline, edge-tts for voiceover, ffmpeg for assembly, and Gemini to QA the result — without touching a video editor."
pubDate: 2026-03-02
tags: ["AI", "Automation", "Playwright", "Developer Productivity", "Video"]
lang: en
translationKey: automated-demo-recording-playwright
heroImage: "/blog/automated-demo-recording-playwright.png"
---

I needed a demo video for an RFP automation platform I'm building. The typical approach: record your screen, stumble through clicks, re-record when something breaks, then spend an hour in a video editor syncing voiceover. I've done it before. It's painful.

So I tried a different approach: **let AI do the whole thing**.

- **Claude Code** wrote the entire recording pipeline — Playwright scripts, ffmpeg assembly, speed control, subtitle generation
- **edge-tts** generated the narration with Microsoft's neural voices
- **Gemini 3.1 Pro** reviewed the final video for audio/video sync issues

The result: a 3-minute narrated demo with 14 scenes, variable speed segments, and subtitles. No video editor. No screen recording app. No manual voiceover.

<div style="position: relative; padding-bottom: 56.25%; height: 0;"><iframe src="https://www.loom.com/embed/b17966fe959e41cabf4b02b12ddccac4" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"></iframe></div>

Here's how the whole process worked — including the parts that broke.

## The Pipeline

```
Playwright (record) → edge-tts (voice) → ffmpeg (assemble) → Gemini (QA)
```

### Step 1: Claude Code Writes the Recorder

I described what I wanted: a demo video using Playwright to record the browser, with text-to-speech for coordinated voiceover, covering the full application workflow. Claude Code decided the structure — 14 scenes from dashboard to API docs — wrote the scene scripts, and generated the modules. Each one is a TypeScript function that drives the browser through a specific feature:

```typescript
export const scene: SceneFn = async (page) => {
  await page.getByText("Generate Answer").click();

  // Wait for AI to finish
  const indicator = page.getByText("Generating AI answer...");
  await indicator.waitFor({ state: "hidden", timeout: 90_000 });

  // Scroll through the answer smoothly
  const scrollPanel = page.locator("[data-demo-scroll=true]");
  await scrollPanel.evaluate((el) => {
    el.scrollTo({ top: el.scrollHeight / 3, behavior: "smooth" });
  });
  await longPause(page);
};
```

A test wrapper runs all 14 scenes in sequence, recording timestamps:

```typescript
for (const id of sceneIds) {
  const start = (Date.now() - videoStartTime) / 1000;
  await SCENES[id](page);
  timestamps.push({ id, start, end: (Date.now() - videoStartTime) / 1000 });
}
```

Output: one `.webm` video + a `scene-timestamps.json` file. This separation is key — it lets us manipulate each scene independently during assembly.

### Step 2: AI Voice with edge-tts

Each scene has a narration line. [edge-tts](https://github.com/rany2/edge-tts) turns them into MP3 files using Microsoft's neural TTS — free, no API key, surprisingly natural:

```bash
edge-tts --text "Let's generate an AI answer..." \
  --voice en-US-GuyNeural \
  --write-media voice/08-generate-answer.mp3
```

14 scenes, 30 seconds to generate all voices. Claude Code wrote the narration script too — I reviewed and tweaked the phrasing, but the drafting was AI.

### Step 3: Assembly — Where Everything Broke

Claude Code also wrote the assembly script. In theory, it's simple: split the video by timestamps, overlay voice, concatenate. In practice, this is where I spent most of the iteration time with Claude.

#### Variable Speed: 30 Seconds of Spinner → 2 Seconds

Nobody wants to watch an AI loading spinner for 30 seconds. The solution: per-scene speed segments.

```typescript
{
  id: "08-generate-answer",
  speed: [
    { from: 0, to: 1, speed: 1 },   // Click button at normal speed
    { from: 1, to: 6, speed: 15 },   // AI generation: 30s → 2s
    { from: 6, to: 10, speed: 1 },   // Read the answer at normal speed
  ],
}
```

The `from/to` values are proportional (0-10 scale). ffmpeg applies this via a split/trim/setpts/concat filtergraph. The result: boring waits are compressed 15x while meaningful interactions play at real speed.

#### The Audio Sync Nightmare

This is the lesson that took the most iterations to learn. When merging voice with video per-scene, then concatenating:

**Problem 1:** Using ffmpeg's `-shortest` flag silently truncates the longer stream. Voice gets cut mid-sentence.

**Problem 2 (the nasty one):** ffmpeg starts each concatenated clip's audio where the **previous clip's audio ended**, not where the video starts. If clip A has 30s video but only 13s audio, clip B's audio starts at t=13 instead of t=30. This causes **progressive drift** — by scene 10, the voice is over a minute behind the visuals.

**The fix:** Every clip's audio track must exactly match its video duration:

```bash
ffmpeg -i video.mp4 -i voice.mp3 \
  -filter_complex "[1:a]adelay=500|500,apad=whole_dur=VIDEO_DURATION[audio]" \
  -map 0:v -map "[audio]" -c:v copy -c:a aac output.mp4
```

`apad=whole_dur` pads the audio with silence to exactly match the video length. No drift possible.

## Gemini 3.1 Pro as Video QA

Here's where it got really interesting. After fixing the pipeline, I needed to verify audio/video sync across 14 scenes. Watching the whole video manually each time is tedious and my ears aren't reliable after the 10th iteration.

I uploaded the video to Gemini 3.1 Pro and asked it to analyze the synchronization — which actions happen visually vs. when the narration describes them.

### On the Broken Version

Gemini caught every single sync issue with precise timestamps:

| Action | Visual | Audio | Drift |
|--------|--------|-------|-------|
| Create RFP | 01:51 | 02:09 | 18s late |
| Assign Style Guide | 02:20 | 03:05 | 45s late |
| Generate Answer | 02:22 | 03:31 | **1m 9s late** |
| Chat refinement | 03:22 | 03:58 | 36s late |
| Assign team | 03:55 | 04:28 | 33s late |

Classic progressive drift. Each scene's audio shifts further behind because the previous scene's audio track was shorter than its video.

### On the Fixed Version

After applying the `apad` fix, Gemini's analysis: **13 scenes perfect sync, 1 flagged as ~2 seconds late.**

The flagged scene was actually fine — I'd intentionally added a 1.5-second voice delay to let a visual transition settle before narration began. Gemini was being slightly over-strict.

**Score: 0 missed issues, 1 false positive out of 14 scenes.** That's better QA than I'd get from watching the video myself.

## The Human-AI Feedback Loop

The process wasn't "ask Claude once, get perfect video." It was iterative:

1. **Me:** "I want a demo video using Playwright with TTS, covering the full workflow"
2. **Claude:** Decides on 14 scenes, generates the pipeline. First recording works.
3. **Me:** "The voice is desynced from scene 5 onwards"
4. **Claude:** Debugs, discovers `-shortest` issue. Fixes with `apad`.
5. **Me:** "The answer doesn't scroll — you can't see the bullet points"
6. **Claude:** Investigates DOM, finds wrong scroll container. Fixes with programmatic parent discovery.
7. **Me:** "Still no bullet points in the generated answer"
8. **Claude:** Tests via API, finds the AI returns plain text despite HTML instructions. Adds `normalizeAnswerHtml` post-processor.
9. **Me:** "The KB upload scene has too much dead time, and the style guide voice starts too early"
10. **Claude:** Increases speed compression from 4x to 8x, adds 2s voice delay to style guide scene.

Each round: I watch the video, describe what's wrong in plain language, Claude debugs and fixes. The feedback loop is fast because re-recording takes 4 minutes and assembly takes 1 minute.

## What AI Did vs. What I Did

| Task | Who |
|------|-----|
| Write 14 Playwright scene scripts | Claude Code |
| Write assembly pipeline (800 lines) | Claude Code |
| Write speed segment logic | Claude Code |
| Debug audio sync issues | Claude Code |
| Fix scroll container detection | Claude Code |
| Add HTML normalization post-processor | Claude Code |
| Generate voiceover audio | edge-tts |
| QA audio/video synchronization | Gemini 3.1 Pro |
| Write narration text | Claude Code (I reviewed and adjusted) |
| Review video and give feedback | Me |
| Choose what to show and in what order | Me |

The creative direction was mine. Everything else was AI.

## The Final Numbers

```bash
# Record 14 scenes
npx playwright test e2e/tests/demo-record.spec.ts --headed  # ~4 min

# Generate voices
npx tsx scripts/demo-record.ts voice   # ~30 sec

# Assemble with speed control + subtitles
npx tsx scripts/demo-record.ts assemble  # ~1 min
```

- **Output:** 3:47 narrated video, 14 scenes, variable speed, soft subtitles
- **Pipeline code:** ~800 lines TypeScript (assembly) + ~200 lines (scenes)
- **Re-record time:** Under 6 minutes end-to-end
- **Video editors used:** Zero

If the UI changes tomorrow, I update one scene file and re-run. The entire pipeline is version-controlled and reproducible.

## Honest Trade-off: Manual vs. Automated

For the **first iteration**, manually recording your screen while narrating would be faster. A screen recording tool gives you a video in real time — no pipeline to build.

But manual recording has its own costs: you need a quiet environment and a decent microphone, any stumble means re-recording, editing voiceover timing in a video editor is tedious, and audio quality depends entirely on your hardware.

The automated approach pays off from the **second iteration onward**. When the UI changed, I updated one scene file and re-ran. When the narration needed tweaking, I edited a text string — no re-recording my voice. After five rounds of feedback-and-fix, I'd have spent hours in a video editor doing the same thing manually. And if a client asks for a demo next month after a redesign, it's a 6-minute re-run, not a full re-shoot.

## Beyond Demos: Video as QA Evidence

This pipeline was built for a product demo, but the pattern — browser automation producing narrated video — has broader implications.

Think about QA. Today, test evidence is usually a CI log that says `PASS` or `FAIL`. When a client asks "show me that the payment flow works," you re-run the test and hope they trust a green checkmark. Imagine instead handing them a narrated video: the test runs, the voiceover explains each step, and the video is generated automatically on every release. Regression testing becomes not just a technical checkpoint but a reviewable artifact.

The same applies to compliance and auditing. Regulated industries need proof that systems work as specified. A version-controlled pipeline that produces timestamped video evidence on demand is fundamentally different from manual screen recordings buried in a shared drive.

And onboarding — new team members could watch auto-generated walkthroughs that stay current with the actual UI, not documentation screenshots from six months ago.

The underlying shift is that **video is becoming a programmatic output**, not a creative production. When the cost of producing a video drops from hours to minutes, and re-producing it is a single command, you start using video in places where it was never practical before.

## Key Takeaways

1. **Playwright's `recordVideo` is production-quality** for demos — 720p/25fps, no overhead
2. **Never use `-shortest` in ffmpeg** when merging audio streams for concatenation. Use `apad=whole_dur` to match audio duration to video duration exactly.
3. **Variable speed segments** are the difference between a boring demo and a watchable one. 15x compression for loading spinners, 1x for actual interactions.
4. **Gemini 3.1 Pro is a legitimate video QA tool.** Upload a video, ask "is the audio synced with the visuals?" — it'll give you a timestamped report with near-perfect accuracy.
5. **The human-AI feedback loop matters more than getting it right first try.** I described problems in plain language ("the scroll doesn't work"), Claude debugged and fixed. Five iterations to a polished result.
6. **AI is great at automation, humans are great at judgment.** I wrote the narration script and decided what to show. AI did everything else.
7. **When video becomes a command, you use it everywhere.** The same pipeline that records a demo can generate QA evidence, onboarding walkthroughs, or compliance artifacts — all version-controlled and reproducible on every release.

---

*Tools used: [Claude Code](https://claude.ai/claude-code), [Playwright](https://playwright.dev/), [ffmpeg](https://ffmpeg.org/), [edge-tts](https://github.com/rany2/edge-tts), [Gemini 3.1 Pro](https://deepmind.google/technologies/gemini/)*
