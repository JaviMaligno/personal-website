---
title: "An Agent Sees What a Screen Reader Sees"
description: "I had an AI agent drive Photos, Preview and Telegram on my Mac with no API, only the accessibility tree. Then I measured what 23 apps expose to it. What it can't read, and what it can read but not press, is the same thing a screen reader runs into."
pubDate: 2026-11-05
tags: ["AI", "Agents", "Accessibility", "Automation"]
lang: en
translationKey: an-agent-sees-what-a-screen-reader-sees
heroImage: "/blog/an-agent-sees-what-a-screen-reader-sees.png"
linkedinImage: "/blog/an-agent-sees-what-a-screen-reader-sees-thumb.png"
linkedinLinks:
  - label: "agent-desktop"
    url: "https://github.com/vercel-labs/agent-desktop"
---

<style>
.a11y-fig { margin: 2rem 0; }
.a11y-fig svg { width: 100%; height: auto; display: block; }
.a11y-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.6rem; }
</style>

I gave Claude Code one sentence in a terminal: make a collage of my beach photos and send it to my Telegram channel, so I have it on my phone. Four minutes later it was on my phone. Claude Code had opened Photos, selected the album, exported eight pictures, built the collage, checked it in Preview, pasted it into Telegram, written the caption and sent it.

None of those apps has an API for that. Photos doesn't, and I wasn't going to wire up a Telegram bot to post as myself. The agent drove the apps through [agent-desktop](https://github.com/vercel-labs/agent-desktop), an open-source CLI from Vercel Labs that does one thing: it reads each app's **accessibility tree** and acts on it.

That tree is the same structure macOS hands to VoiceOver. So the question that kept coming back while I watched the run was not "can an agent use my Mac". It was: **how much of my Mac can it actually see?**

## One tree, two readers

Every native window on macOS publishes a tree of elements: a role (`button`, `textfield`, `menuitem`), a name, sometimes a value, and the actions it accepts. A screen reader walks that tree and speaks it. agent-desktop walks the same tree and returns it as JSON with a reference for each element, so the agent can say "press `@e12`" instead of guessing coordinates on a screenshot.

<figure class="a11y-fig">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 270" role="img" aria-label="An app window publishes one accessibility tree with roles, names, values and actions. A screen reader and the agent read the same tree; whatever is missing from it is missing for both.">
  <rect x="0" y="0" width="600" height="270" rx="12" fill="#1a1a24"/>
  <rect x="170" y="18" width="260" height="52" rx="10" fill="none" stroke="rgba(255,255,255,0.18)"/>
  <text x="300" y="42" text-anchor="middle" fill="#f8fafc" font-size="15" font-family="Inter,system-ui,sans-serif" font-weight="600">App window</text>
  <text x="300" y="60" text-anchor="middle" fill="#94a3b8" font-size="12" font-family="Inter,system-ui,sans-serif">Telegram, Photos, Preview…</text>
  <path d="M300 70 L300 100" stroke="#64748b" stroke-width="2" marker-end="url(#a11y-arrow)"/>
  <rect x="120" y="104" width="360" height="64" rx="10" fill="rgba(45,212,191,0.08)" stroke="#2dd4bf"/>
  <text x="300" y="130" text-anchor="middle" fill="#5eead4" font-size="15" font-family="Inter,system-ui,sans-serif" font-weight="600">Accessibility tree</text>
  <text x="300" y="152" text-anchor="middle" fill="#e2e8f0" font-size="12.5" font-family="ui-monospace,'JetBrains Mono',monospace">role · name · value · actions</text>
  <path d="M240 168 L150 206" stroke="#64748b" stroke-width="2" marker-end="url(#a11y-arrow)"/>
  <path d="M360 168 L450 206" stroke="#64748b" stroke-width="2" marker-end="url(#a11y-arrow)"/>
  <rect x="40" y="208" width="220" height="46" rx="10" fill="none" stroke="rgba(255,255,255,0.18)"/>
  <text x="150" y="230" text-anchor="middle" fill="#f8fafc" font-size="14" font-family="Inter,system-ui,sans-serif" font-weight="600">VoiceOver</text>
  <text x="150" y="246" text-anchor="middle" fill="#94a3b8" font-size="11.5" font-family="Inter,system-ui,sans-serif">speaks it to a person</text>
  <rect x="340" y="208" width="220" height="46" rx="10" fill="none" stroke="#f59e0b"/>
  <text x="450" y="230" text-anchor="middle" fill="#fbbf24" font-size="14" font-family="Inter,system-ui,sans-serif" font-weight="600">agent-desktop</text>
  <text x="450" y="246" text-anchor="middle" fill="#94a3b8" font-size="11.5" font-family="Inter,system-ui,sans-serif">returns it as JSON to an agent</text>
  <defs><marker id="a11y-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker></defs>
</svg>
<figcaption>One structure, two readers. Whatever an app leaves out of its tree is invisible to both.</figcaption>
</figure>

That framing changes what "computer use" means. It isn't vision. The agent doesn't look at pixels; it reads what the app chose to describe about itself. If the app describes itself well, the agent is fast and precise. If it doesn't, there is nothing to read.

## What 23 apps expose

So I measured it. I opened the apps I have installed, one at a time, and read the main window's tree with agent-desktop three times each: how many elements it exposes, what share of them have a name, and how many accept an action. Only counts, no content.

<img src="https://www.javieraguilar.ai/blog/an-agent-sees-what-a-screen-reader-sees-census.png" alt="Bar chart of accessibility tree size per app: Telegram 1,493 elements with 100% named, Spotify 1,221, Slack 616, ChatGPT 406, down to TextEdit 13, the Android emulator with a single element and Docker Desktop not answering in 45 seconds." />

A few things stood out:

- **Telegram exposes 1,493 elements and every single one has a name.** Each chat, each message, each counter. For an agent it is the most legible app on the machine.
- **Spotify exposes almost as many, but half of them unnamed.** A button with no name is a button the agent has to guess. A screen reader user has to guess too.
- **The Android emulator exposes one element: the window.** The whole phone inside it is a picture. The agent can see that there is a window called "Android Emulator" and nothing else.
- **Docker Desktop didn't answer at all.** Three reads, 45 seconds each, no tree.
- **ChatGPT went from 12 elements to 406** between the first read and the second. Just opened, it exposed a shell; a few seconds later, the whole interface. Measuring cold would have called it opaque.
- **The Terminal exposes 17 elements**, because the entire transcript is one text field. The agent can read it, but as one block of text, not as structure.

Two caveats. These are counts from one machine on one day, of whatever window each app opened with, and a bigger tree is not automatically a more usable one. The share of named elements says more than the size. But the extremes are not subtle: between "one element" and "1,493 named elements" there is no measurement error that changes the conclusion.

I later repeated the census on a Windows 11 machine, where agent-desktop reads the UI Automation tree instead, and the picture held. The same app reads about the same on both systems: Telegram exposes 1,509 elements there against 1,493 here, Slack 483 against 616. The cold first read happens there too: Spotify gave 183 elements, then 1,651. Of the rules further down, the one about the current desktop held; the other two didn't, because on Windows a background app's menu reads as enabled and the save dialog belongs to the app's own process.

## Exposed is not the same as operable

The collage run taught me the second half, and it's the part a census doesn't show. Telegram, the most legible app in the chart, was also where the agent struggled most.

To send an image it pastes it into the message box and Telegram opens a send panel with a caption field and two buttons. Everything in that panel is in the tree, with good names. And yet:

<figure class="a11y-fig">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 300" role="img" aria-label="Telegram's send panel shows a caption that reads 'Done, 8 beach photos, one collage' and a Send button. In the accessibility tree the caption field's value is empty and the Send and Cancel buttons expose no press action.">
  <rect x="0" y="0" width="600" height="300" rx="12" fill="#1a1a24"/>
  <text x="155" y="30" text-anchor="middle" fill="#94a3b8" font-size="12.5" font-family="Inter,system-ui,sans-serif" letter-spacing="1.5">ON SCREEN</text>
  <text x="445" y="30" text-anchor="middle" fill="#94a3b8" font-size="12.5" font-family="Inter,system-ui,sans-serif" letter-spacing="1.5">IN THE TREE</text>
  <rect x="20" y="44" width="270" height="236" rx="12" fill="#232331" stroke="rgba(255,255,255,0.1)"/>
  <text x="38" y="72" fill="#f8fafc" font-size="14" font-family="Inter,system-ui,sans-serif" font-weight="600">Send an image</text>
  <g fill="#2a3b4a"><rect x="38" y="84" width="56" height="34" rx="3"/><rect x="98" y="84" width="56" height="34" rx="3"/><rect x="158" y="84" width="56" height="34" rx="3"/><rect x="218" y="84" width="56" height="34" rx="3"/></g>
  <g fill="#4a3424"><rect x="38" y="122" width="56" height="34" rx="3"/><rect x="98" y="122" width="56" height="34" rx="3"/><rect x="158" y="122" width="56" height="34" rx="3"/><rect x="218" y="122" width="56" height="34" rx="3"/></g>
  <text x="38" y="186" fill="#5eead4" font-size="11.5" font-family="Inter,system-ui,sans-serif">Caption</text>
  <text x="38" y="206" fill="#f8fafc" font-size="13" font-family="Inter,system-ui,sans-serif">Done ✅ — 8 beach photos, one collage.</text>
  <line x1="38" y1="214" x2="272" y2="214" stroke="#2dd4bf" stroke-width="1.5"/>
  <text x="172" y="258" fill="#5eead4" font-size="13.5" font-family="Inter,system-ui,sans-serif">Cancel</text>
  <text x="236" y="258" fill="#5eead4" font-size="13.5" font-family="Inter,system-ui,sans-serif" font-weight="600">Send</text>
  <rect x="310" y="44" width="270" height="236" rx="12" fill="#14141c" stroke="rgba(255,255,255,0.1)"/>
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="13">
    <text x="328" y="82" fill="#5eead4">textfield<tspan fill="#e2e8f0"> "Caption"</tspan></text>
    <text x="344" y="106" fill="#94a3b8">value: <tspan fill="#fbbf24">""</tspan></text>
    <text x="328" y="150" fill="#5eead4">button<tspan fill="#e2e8f0"> "Send"</tspan></text>
    <text x="344" y="174" fill="#94a3b8">press: <tspan fill="#fbbf24">not available</tspan></text>
    <text x="328" y="218" fill="#5eead4">button<tspan fill="#e2e8f0"> "Cancel"</tspan></text>
    <text x="344" y="242" fill="#94a3b8">press: <tspan fill="#fbbf24">not available</tspan></text>
  </g>
</svg>
<figcaption>Named, but not operable. The caption is on screen and empty in the tree; the buttons are listed and can't be pressed.</figcaption>
</figure>

- **The caption field reports an empty value** while the screen clearly shows the text. The agent couldn't confirm what it had typed by reading; it had to take a screenshot of that area and look.
- **Send and Cancel accept no press action.** The tool refused to click them semantically, and a physical click through the tool failed too. What worked was the keyboard: Enter sends, Escape cancels.
- **Even typing failed there.** The field never reported having focus, so the tool wouldn't type into it. The workaround was to put the text on the clipboard and paste.

Telegram isn't alone. Other things I hit along the way, each turned into a rule the agent now follows:

- **Menus only work in the frontmost app.** Ask Photos for File › Export while it's in the background and the item reads as *disabled*. Bring the app forward and it's enabled.
- **The save dialog is a different process.** The panel where you choose a folder doesn't belong to Photos, so keyboard shortcuts sent to Photos never reach it. In one rehearsal, a semantic click on a folder inside it saved the export straight into that folder.
- **Actions can land late.** A paste that seemed not to have worked showed up a moment later, and the panel ended up with two copies of the image. Every step needs a fresh look before the next one.
- **The agent only sees the current desktop.** Switch to another macOS Space and every window there disappears from the tree.
- **Some trees are too big to read whole.** A long Telegram chat produced a tree over the tool's 1 MB limit; the agent had to read the window shallowly and then drill into the message list.

None of these is exotic. They're the same seams a keyboard or screen-reader user hits: a value the app doesn't publish, a control with no action, a dialog in another process.

## What a screen reader user would get

I didn't run these tasks with VoiceOver, so I'll be careful here. But VoiceOver asks the same API the same questions. A caption field that reports an empty value is, to it, an empty field. A button with no press action is a button that VoiceOver's own activate command has nothing to call; it would have to fall back to simulating a mouse click, as the agent did. An emulator window with one element is, to a blind user, one unlabelled window.

The difference is who pays. A screen reader user meets these gaps one at a time and works around them with patience. An agent meets them too, but then they become rules: "press Enter, the button doesn't take clicks", "paste, don't type". The workarounds the agent needed are a map of where an app's accessibility is broken.

It reminded me of what I found [measuring agents on degraded code](/en/blog/practices-for-agents-substrate): in large repositories, how the code is written halves what an agent solves. Here it's the same lesson one layer up. The agent is only as good as what it can read, and what it can read is whatever someone bothered to describe.

## If you build apps, or agents

**If you build apps:** accessibility used to be about people who use assistive technology. It still is, and that alone is reason enough. But the same tree is now the interface for every agent that operates a computer the way a person would. Name your controls, publish your values, give your buttons a press action. That's the whole checklist, and it serves both readers at once.

**If you build agents on top of this:** treat each app as having its own rules, and verify after every action, because the tree will sometimes tell you something worked when it didn't, or that it failed when it hadn't. The run that finally went clean, in a bit under four minutes, wasn't a smarter model. It was a short list of what each app lets you do.

If an app is accessible, it's a tool. If it isn't, for an agent it barely exists.

---

*Measured on macOS 15.7 with [agent-desktop](https://github.com/vercel-labs/agent-desktop) 1.0.2: main window of each app, three reads, counts only. Figma and Cursor didn't launch from the command line on this machine and aren't in the chart.*
