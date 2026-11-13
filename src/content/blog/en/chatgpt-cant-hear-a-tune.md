---
title: "ChatGPT Reads the Lyrics, Not the Tune"
description: "I hummed Happy Birthday to ChatGPT and it could not name it; with the words it answered at once. Then I ran 150 wordless recordings through OpenAI's voice models: they name a song from its lyrics and are at chance without them, while a tiny contour model got my three hums right."
pubDate: 2026-12-17
tags: ["AI", "Voice", "Evaluation", "Multimodal", "Machine Learning"]
lang: en
translationKey: chatgpt-cant-hear-a-tune
heroImage: "/blog/chatgpt-cant-hear-a-tune.png"
---

When you talk to ChatGPT it feels like it is listening. I wanted to know what actually arrives on the other side, so I picked the simplest thing a voice carries besides words: a melody. I hummed Happy Birthday to ChatGPT, in every way the app lets me speak to it, and then ran the same question at scale through the voice models OpenAI sells to developers.

<style>
.hum-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.hum-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.hum-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

## Two buttons, two different things

**The microphone and the voice button do not do the same job.** The small microphone is Dictation: [OpenAI's help page](https://help.openai.com/en/articles/20001274-chatgpt-voice) describes it as turning a recording into editable text, which you then send like anything you typed. The other button opens Voice, a spoken conversation that today runs on a model called GPT-Live-1.1.

<figure class="hum-fig">
<svg viewBox="0 0 600 230" role="img" aria-label="Dictation turns the voice into text before the model sees it, so a hum arrives as an empty message; Voice sends the sound itself to a voice model">
  <defs>
    <marker id="hum-ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker>
  </defs>
  <text x="20" y="28" fill="#94a3b8" font-size="13">Dictation (microphone button)</text>
  <rect x="20" y="42" width="110" height="46" rx="8" fill="none" stroke="#64748b"/>
  <text x="75" y="70" fill="#e2e8f0" font-size="13" text-anchor="middle">my hum</text>
  <rect x="175" y="42" width="120" height="46" rx="8" fill="none" stroke="#f59e0b"/>
  <text x="235" y="70" fill="#fbbf24" font-size="13" text-anchor="middle">transcriber</text>
  <rect x="340" y="42" width="100" height="46" rx="8" fill="none" stroke="#64748b"/>
  <text x="390" y="70" fill="#e2e8f0" font-size="13" text-anchor="middle">text: ""</text>
  <rect x="485" y="42" width="95" height="46" rx="8" fill="none" stroke="#64748b"/>
  <text x="532" y="70" fill="#e2e8f0" font-size="13" text-anchor="middle">text model</text>
  <g stroke="#64748b" stroke-width="2" fill="none" marker-end="url(#hum-ar)"><path d="M130,65 H170"/><path d="M295,65 H335"/><path d="M440,65 H480"/></g>
  <text x="20" y="140" fill="#94a3b8" font-size="13">Voice (the button that talks back)</text>
  <rect x="20" y="154" width="110" height="46" rx="8" fill="none" stroke="#64748b"/>
  <text x="75" y="182" fill="#e2e8f0" font-size="13" text-anchor="middle">my hum</text>
  <rect x="340" y="154" width="240" height="46" rx="8" fill="none" stroke="#2dd4bf"/>
  <text x="460" y="182" fill="#5eead4" font-size="13" text-anchor="middle">voice model (hears the sound)</text>
  <g stroke="#64748b" stroke-width="2" fill="none" marker-end="url(#hum-ar)"><path d="M130,177 H335"/></g>
  <text x="232" y="170" fill="#94a3b8" font-size="12" text-anchor="middle">audio</text>
</svg>
<figcaption>With Dictation the model only ever sees text, and a hum has no text. With Voice the sound itself reaches a model, so the question becomes what that model does with it.</figcaption>
</figure>

**Dictation wrote nothing.** I hummed Happy Birthday twice, once as "hmmm" and once as "na na na", and both times the text box stayed empty. That is the expected outcome of a transcriber: there were no words to write down.

**Voice told me it could not do it.** I said I was going to hum a song and asked which one it was. Before I had hummed a note it answered, in Spanish, which is how I was speaking to it:

> I'd love to, but right now I can't identify songs from humming or melodies. We're working on it and I'll be able to soon. If you like, tell me a line of the lyrics and we'll see if we can track it down together.

I tried again in a new chat, humming with no warning and then asking what song it was, and got the same answer. Then I sang "Cumpleaños feliz" with its words, and it replied at once that it was Happy Birthday.

So the product is honest about the limit. What I could not tell from the app is whether the model behind it hears a melody and is held back, or does not hear it well enough to try. For that I went to the models directly.

## The same question, through the API

**I tested three ways of getting a voice into an OpenAI model**, all deployed on Azure OpenAI:

- **Transcribe, then ask**: `gpt-4o-mini-transcribe` writes down the audio and `gpt-6-luna`, a text model, answers from the transcript. This is what Dictation does, and it is also the baseline that hears nothing but words.
- **`gpt-audio-1.5`**: a chat model that takes the audio file as input.
- **`gpt-realtime-2.1`**: the speech-to-speech model developers use to build voice agents.

None of these is GPT-Live, the model inside ChatGPT's Voice, which I could only test through the app. They are OpenAI's voice models as a developer gets them.

For recordings I used [MTG-QBH](https://zenodo.org/records/1290712), a research set of 118 clips of people singing or humming pop songs with no accompaniment. I took the first 20 seconds of each and asked every route which song it was. A text model graded the answers, and I checked its verdicts against a literal title match. From two transcripts per clip I sorted them into 76 sung with lyrics, 30 with no words at all, and 12 in between.

<figure class="hum-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="With lyrics the three routes name between 71 and 74 of 76 songs; without words they name 0, 1 and 1 of 30">
  <line x1="50" y1="210" x2="570" y2="210" stroke="#64748b"/>
  <g font-size="12" fill="#e2e8f0" text-anchor="middle">
    <rect x="80" y="70" width="50" height="140" fill="#64748b"/><text x="105" y="62">71/76</text>
    <rect x="150" y="70" width="50" height="140" fill="#f59e0b"/><text x="175" y="62">71/76</text>
    <rect x="220" y="64" width="50" height="146" fill="#2dd4bf"/><text x="245" y="56">74/76</text>
    <rect x="350" y="209" width="50" height="1" fill="#64748b"/><text x="375" y="200">0/30</text>
    <rect x="420" y="205" width="50" height="5" fill="#f59e0b"/><text x="445" y="196">1/30</text>
    <rect x="490" y="205" width="50" height="5" fill="#2dd4bf"/><text x="515" y="196">1/30</text>
  </g>
  <g font-size="13" fill="#e2e8f0" text-anchor="middle">
    <text x="175" y="232">Sung with lyrics</text>
    <text x="445" y="232">No words</text>
  </g>
  <g font-size="12" fill="#94a3b8">
    <rect x="70" y="248" width="10" height="10" fill="#64748b"/><text x="86" y="257">transcribe, then ask</text>
    <rect x="250" y="248" width="10" height="10" fill="#f59e0b"/><text x="266" y="257">gpt-audio-1.5</text>
    <rect x="400" y="248" width="10" height="10" fill="#2dd4bf"/><text x="416" y="257">gpt-realtime-2.1</text>
  </g>
</svg>
<figcaption>Songs named correctly on MTG-QBH. The route that only reads a transcript does as well as the two that receive the audio, and all three collapse when the words go away.</figcaption>
</figure>

**With lyrics, the route that only reads a transcript named 71 of 76 songs, the same as `gpt-audio-1.5`.** `gpt-realtime-2.1` named 74. The audio added nothing I could measure over the words. Without words, the three routes named 0, 1 and 1 of 30, and the single hit was "Ob-La-Di, Ob-La-Da", whose syllables are the title.

**When `gpt-realtime-2.1` did guess, it guessed "Hey Jude".** I ran each wordless clip three times: 64 of its 90 answers were "unknown" and 19 were "Hey Jude", for hums of "Bohemian Rhapsody", "Smells Like Teen Spirit" or "Sweet Home Alabama". A "na na na" was enough to call it.

## Maybe they hear it and cannot name it

**The obvious objection is that naming a song is hard even if you hear the melody.** So I made the task easy. [MLEnd Hums and Whistles](https://www.kaggle.com/datasets/jesusrequena/mlend-hums-and-whistles) is a set of people humming and whistling eight film songs. I sampled 120 hums, 15 per song, from 95 different people, and gave the model the list of eight to choose from. Guessing blindly scores 12.5 %.

`gpt-realtime-2.1` picked the right one in 11 of 120, or 9 %. The transcript-only baseline, which for most of these clips received an empty transcript, got 16 of 120. Hearing the hum was no better than not hearing it.

<figure class="hum-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Each of the eight songs was hummed 15 times, but gpt-realtime-2.1 chose Harry Potter 50 times, The Pink Panther 37 and Star Wars 32, and almost never the other five">
  <g font-size="12.5" fill="#e2e8f0" text-anchor="end">
    <text x="165" y="39">Harry Potter theme</text><text x="165" y="69">The Pink Panther theme</text><text x="165" y="99">Star Wars theme</text><text x="165" y="129">Singin' in the Rain</text><text x="165" y="159">Hakuna Matata</text><text x="165" y="189">Mamma Mia</text><text x="165" y="219">The Greatest Showman</text><text x="165" y="249">Let It Go</text>
  </g>
  <g fill="#2dd4bf">
    <rect x="175" y="26" width="300" height="18"/><rect x="175" y="56" width="222" height="18"/><rect x="175" y="86" width="192" height="18"/><rect x="175" y="116" width="6" height="18"/>
    <rect x="175" y="146" width="1" height="18"/><rect x="175" y="176" width="1" height="18"/><rect x="175" y="206" width="1" height="18"/><rect x="175" y="236" width="1" height="18"/>
  </g>
  <g font-size="12" fill="#5eead4">
    <text x="481" y="40">50</text><text x="403" y="70">37</text><text x="373" y="100">32</text><text x="187" y="130">1</text><text x="182" y="160">0</text><text x="182" y="190">0</text><text x="182" y="220">0</text><text x="182" y="250">0</text>
  </g>
  <line x1="265" y1="18" x2="265" y2="262" stroke="#f59e0b" stroke-dasharray="5 4" stroke-width="2"/>
  <text x="271" y="282" fill="#fbbf24" font-size="12">each song was hummed 15 times</text>
</svg>
<figcaption>What gpt-realtime-2.1 chose for 120 hums when given the eight titles. It spread its answers over three of them whatever was hummed, which is what choosing without hearing the melody looks like.</figcaption>
</figure>

**Its choices did not follow the audio.** Every song was hummed 15 times, yet the model answered Harry Potter 50 times, The Pink Panther 37 and Star Wars 32, and the other five songs once between them. Asked openly, with no list, it named 1 hum of 119.

## My own voice, and a model that does hear it

**I recorded myself so I could hold the song fixed and change one thing at a time.** Four hums (Happy Birthday, Ode to Joy, Jingle Bells and The Beatles' "Dear Prudence"), Happy Birthday sung with its words, and one trick recording: the words of Happy Birthday sung to the tune of Jingle Bells.

<figure class="hum-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="None of the OpenAI routes named any of my four hums, all named the song once it had words, and all said the tune of the crossed recording was Happy Birthday; hum2song ranked the right tune first for the three hums in its catalogue">
  <g font-size="12" fill="#94a3b8" text-anchor="middle">
    <text x="262" y="24">transcribe,</text><text x="262" y="38">then ask</text><text x="352" y="31">gpt-audio-1.5</text><text x="447" y="31">gpt-realtime-2.1</text><text x="540" y="31">hum2song</text>
  </g>
  <g font-size="12.5" fill="#e2e8f0">
    <text x="14" y="72">Hummed: Happy Birthday</text><text x="14" y="108">Hummed: Ode to Joy</text><text x="14" y="144">Hummed: Jingle Bells</text><text x="14" y="180">Hummed: Dear Prudence</text><text x="14" y="216">Sung with its words</text><text x="14" y="246">Happy Birthday words,</text><text x="14" y="261">Jingle Bells tune</text>
  </g>
  <g font-size="13" text-anchor="middle">
    <g fill="#94a3b8"><text x="262" y="72">no</text><text x="352" y="72">0 of 3</text><text x="447" y="72">0 of 3</text><text x="262" y="108">no</text><text x="352" y="108">0 of 3</text><text x="447" y="108">0 of 3</text><text x="262" y="144">no</text><text x="352" y="144">0 of 3</text><text x="447" y="144">0 of 3</text><text x="262" y="180">no</text><text x="352" y="180">0 of 3</text><text x="447" y="180">0 of 3</text><text x="540" y="180">not in its list</text><text x="540" y="216">–</text><text x="540" y="254">–</text></g>
    <g fill="#5eead4"><text x="540" y="72">1st of 15</text><text x="540" y="108">1st of 15</text><text x="540" y="144">1st of 15</text><text x="262" y="216">yes</text><text x="352" y="216">3 of 3</text><text x="447" y="216">3 of 3</text></g>
    <g fill="#fbbf24"><text x="352" y="254">tune: Happy Birthday (all 7 answers)</text></g>
  </g>
  <g stroke="rgba(255,255,255,0.1)"><line x1="10" y1="48" x2="590" y2="48"/><line x1="10" y1="194" x2="590" y2="194"/><line x1="10" y1="228" x2="590" y2="228"/></g>
</svg>
<figcaption>My recordings. The three OpenAI routes fail on every hum and succeed as soon as there are words; a small model that only sees the melody's contour finds the three hums it has in its catalogue.</figcaption>
</figure>

**No route named any of the four hums; all of them named the song once it had words.** The trick recording is the clearest result. I asked separately for the song the words belong to and the song the tune belongs to, and all seven answers said the tune was Happy Birthday. Asked directly about the melody, the models answered from the lyrics.

**A small model that looks only at the melody had no trouble.** [hum2song](https://github.com/luiginotmario/hum2song) is an open model that turns the pitch contour of a recording, how the note moves up and down over time, into a vector and compares it with the contours of known tunes. It runs on my laptop. I gave it a catalogue of 15 well-known melodies and my three hums that are in it, and it ranked the right tune first for each. Given the same list of 15 to choose from, `gpt-realtime-2.1` picked the right one in 0 of 9 tries and `gpt-audio-1.5` in 2 of 9; the transcript-only route, with nothing to go on, got 1 of 3. Three hums by one person are an example, not a measurement, but they show the information is in the recording.

## What does get through

**The voice models are not deaf to everything beyond words.** On [RAVDESS](https://zenodo.org/records/1188976), where actors say the same sentence in different emotions, I used 48 clips across four emotions: `gpt-audio-1.5` got the emotion in 37 and `gpt-realtime-2.1` in 28 of 47, against 12 expected by chance. And when I sang two notes more than an octave apart, `gpt-realtime-2.1` said which was higher all six times I asked.

So some of the sound arrives: enough for a coarse emotion or a wide jump in pitch, not enough to follow a melody. That is the precise version of the title. Tone of voice was something I only probed, and I will not claim more for it than those numbers.

## What I take from it

**If the words are the same, assume the model got the same message.** That is the practical reading for anyone building on these models, a phone agent for customer service for example: a pipeline that transcribes first hands the model text and nothing else, and a speech-to-speech model hears more than that, but less than the conversation feels like.

This is the same shape I found with images in [One Grey Level Out of 255](/en/blog/perception-edges-of-language): what a model perceives is not what I would perceive in its place, in either direction, and the only way to know is to measure.

The limits are worth stating. I tested ChatGPT itself by hand, a few times, in Spanish, and it declined rather than tried. The measurements are on three OpenAI models through the API, on the first 15 to 20 seconds of each recording, and the MTG-QBH clips come from only 17 singers. I did not test other companies' models.

ChatGPT says it is working on this, and it may be fixed by the time you read it. The interesting question is the one behind it: what would it take for a model like this to hear a tune, and whether handing it a tool that does is the shorter road. That is the next piece.
