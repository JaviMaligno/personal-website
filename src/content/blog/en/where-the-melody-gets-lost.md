---
title: "A 1990s Trick Hears the Tune a Voice Model Can't"
description: "Voice models from OpenAI and Alibaba are at chance naming a hummed song from a list of eight. A pitch-contour search from the 1990s gets 46 %, and handed to a text model as a tool it fixes the problem for cents. Probing a speech encoder layer by layer shows where the melody goes."
pubDate: 2026-12-17
tags: ["AI", "Voice", "Evaluation", "Multimodal", "Machine Learning"]
lang: en
translationKey: where-the-melody-gets-lost
heroImage: "/blog/where-the-melody-gets-lost.png"
---

In [the previous article](/en/blog/chatgpt-cant-hear-a-tune) I hummed songs to ChatGPT and to OpenAI's voice models and found that they name a song from its lyrics and are lost without them. That left the question I actually cared about: why, and what it would take to fix it. I kept the same 120 recordings and changed what listens to them.

<style>
.mel-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.mel-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.mel-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

## Hearing a tune is not recognising it

**These are two different abilities, and the second one needs a catalogue.** To hear a melody is to keep its shape: this note, then a higher one, then a long lower one. To recognise it is to match that shape against melodies you already know. A person who has never heard a song can hum it back and still not name it.

The systems that do this well are built around that split. Shazam does not hear melodies at all: [its published method](https://www.ee.columbia.edu/~dpwe/papers/Wang03-shazam.pdf) fingerprints one specific recording from the peaks of its spectrogram, so it finds the studio track playing in a bar and has nothing to match when you hum. Google's hum search goes the other way. [Google describes](https://research.google/blog/the-machine-learning-behind-hum-to-search/) a network that turns audio into an embedding of the melody alone, trained so that a hum lands near the recording of the same tune, searched against more than half a million songs.

A voice model has neither piece by design. It was trained to understand speech, and whatever it knows about melodies it picked up on the side.

## The oldest method in the book

**Query by humming is a research field from the 1990s, and its first recipe fits in three steps.** Track the pitch of the voice. Throw away the key, so it does not matter how high the person sings. Compare the resulting contour with the contours you have, stretching time so tempo does not matter either.

I wrote that recipe as a short script, with a standard pitch tracker and dynamic time warping, the classic way to compare two curves that run at different speeds. The recordings are the 120 hums from [MLEnd Hums and Whistles](https://www.kaggle.com/datasets/jesusrequena/mlend-hums-and-whistles) that I used before: eight film songs, 15 hums each, 95 people. For every hum, the search looks for the closest hum by a different person and answers with that person's song. No neural network anywhere.

<figure class="mel-fig">
<svg viewBox="0 0 600 210" role="img" aria-label="Choosing among eight songs for 120 hums, the two voice models that hear the audio name 11 and 12, below the 15 expected by chance, while a contour search names 55 and a text model using that search as a tool names 56">
  <text x="260" y="36" fill="#e2e8f0" font-size="12.5" text-anchor="end">Guessing blindly</text>
  <rect x="270" y="22" width="34" height="20" fill="#64748b"/>
  <text x="311" y="37" fill="#e2e8f0" font-size="12.5">15</text>
  <text x="260" y="70" fill="#e2e8f0" font-size="12.5" text-anchor="end">gpt-realtime-2.1, hears the audio</text>
  <rect x="270" y="56" width="25" height="20" fill="#f59e0b"/>
  <text x="302" y="71" fill="#e2e8f0" font-size="12.5">11</text>
  <text x="260" y="104" fill="#e2e8f0" font-size="12.5" text-anchor="end">Qwen2.5-Omni-3B, hears the audio</text>
  <rect x="270" y="90" width="27" height="20" fill="#f59e0b"/>
  <text x="304" y="105" fill="#e2e8f0" font-size="12.5">12</text>
  <text x="260" y="138" fill="#e2e8f0" font-size="12.5" text-anchor="end">Contour search (1990s method)</text>
  <rect x="270" y="124" width="124" height="20" fill="#2dd4bf"/>
  <text x="401" y="139" fill="#e2e8f0" font-size="12.5">55</text>
  <text x="260" y="172" fill="#e2e8f0" font-size="12.5" text-anchor="end">Text model + contour search as a tool</text>
  <rect x="270" y="158" width="126" height="20" fill="#2dd4bf"/>
  <text x="403" y="173" fill="#e2e8f0" font-size="12.5">56</text>
</svg>
<figcaption>Hums named out of 120, choosing among eight film songs. The models that receive the sound do no better than guessing; a search over the shape of the melody gets almost half, with or without a language model reading its output.</figcaption>
</figure>

**It named 55 of 120, or 46 %, where guessing gets 12.5 %.** On the same recordings and the same eight options, `gpt-realtime-2.1`, OpenAI's speech-to-speech model, named 11. So the melody is in the recording and a very old technique gets it out. The problem is not hard in the way that would excuse a large model.

Two cautions on that 46 %. It is a choice among eight songs, with other people's hums of those same songs as the reference, not recognition against a real catalogue. And it is the plainest version of the method: people hum different passages of each theme, which accounts for part of the misses.

## Not only OpenAI

**An open model from another company fails the same way.** I ran Qwen2.5-Omni-3B, Alibaba's open audio model, on the same hums and prompts. Asked openly what the song was, it answered "unknown" all 120 times. Given the eight options it was right 12 times, and it answered "1" in 80 of the 120, the first item on the list whatever was hummed.

This matches what the benchmarks say about pitch in general. In [PitchBench](https://arxiv.org/abs/2605.26176), a set of pitch tasks on synthesised tones, the strongest audio language model averages 53.9 % while a classical signal-processing baseline scores 73.2 %. The model I could run is the small one of its family; its larger siblings top those benchmarks and I could not fit them on a free GPU.

## The fix is a tool

**If the model cannot hear the tune, give it something that can.** I turned the contour search into a tool: it returns its five closest matches with their titles, and a text model, `gpt-6-luna`, answers from that list without ever receiving the audio.

It named 56 of 120 choosing among the eight, and 40 of 120 with the open question, against 11 and 1 for the voice model that hears the recording. The whole run cost two cents. The right song was among the tool's five matches for 97 of the 120 hums, so most of the remaining error belongs to my minimal search, and a better one would lift the result.

In the first article a small trained model, [hum2song](https://github.com/luiginotmario/hum2song), ranked my own three hums first among fifteen tunes. It is the learned version of the same idea: reduce the recording to its contour, compare contours.

**What I could not do is skip the catalogue.** I also tried handing a text model the notes themselves. With clean synthesised tones of four classic tunes it named all four from the note list. With real singers and 118 pop songs, the same route named none. A language model has a thin memory of melodies as notes: enough for Happy Birthday, not for pop. Recognition needs the list of songs to compare against, which is exactly what a search tool carries.

## Where the melody goes

**I wanted to see the loss happen, so I looked inside an encoder.** OpenAI does not publish how its voice models take audio in, but it does publish [Whisper](https://arxiv.org/abs/2212.04356), its speech recognition model, whose encoder is the standard open front end for speech. I ran the 120 hums through it and, at each of its twelve layers, tried to read the pitch back with the simplest possible probe: a straight-line fit, tested on singers it had not seen.

<figure class="mel-fig">
<svg viewBox="0 0 600 280" role="img" aria-label="A linear read-out of pitch from the Whisper encoder correlates 0.69 with the true pitch at the input, 0.90 at layers 2 and 3, and falls steadily to 0.63 at the last layer">
  <line x1="70" y1="210" x2="570" y2="210" stroke="rgba(255,255,255,0.08)"/>
  <text x="62" y="214" fill="#94a3b8" font-size="11" text-anchor="end">0.5</text>
  <line x1="70" y1="174" x2="570" y2="174" stroke="rgba(255,255,255,0.08)"/>
  <text x="62" y="178" fill="#94a3b8" font-size="11" text-anchor="end">0.6</text>
  <line x1="70" y1="138" x2="570" y2="138" stroke="rgba(255,255,255,0.08)"/>
  <text x="62" y="142" fill="#94a3b8" font-size="11" text-anchor="end">0.7</text>
  <line x1="70" y1="102" x2="570" y2="102" stroke="rgba(255,255,255,0.08)"/>
  <text x="62" y="106" fill="#94a3b8" font-size="11" text-anchor="end">0.8</text>
  <line x1="70" y1="66" x2="570" y2="66" stroke="rgba(255,255,255,0.08)"/>
  <text x="62" y="70" fill="#94a3b8" font-size="11" text-anchor="end">0.9</text>
  <line x1="70" y1="30" x2="570" y2="30" stroke="rgba(255,255,255,0.08)"/>
  <text x="62" y="34" fill="#94a3b8" font-size="11" text-anchor="end">1.0</text>
  <polyline points="70,142 108,93 147,69 185,66 224,66 262,69 301,74 339,80 378,95 416,103 455,119 493,131 532,141 570,164" fill="none" stroke="#2dd4bf" stroke-width="2.5"/>
  <circle cx="70" cy="142" r="3.5" fill="#2dd4bf"/>
  <circle cx="108" cy="93" r="3.5" fill="#2dd4bf"/>
  <circle cx="147" cy="69" r="3.5" fill="#2dd4bf"/>
  <circle cx="185" cy="66" r="3.5" fill="#2dd4bf"/>
  <circle cx="224" cy="66" r="3.5" fill="#2dd4bf"/>
  <circle cx="262" cy="69" r="3.5" fill="#2dd4bf"/>
  <circle cx="301" cy="74" r="3.5" fill="#2dd4bf"/>
  <circle cx="339" cy="80" r="3.5" fill="#2dd4bf"/>
  <circle cx="378" cy="95" r="3.5" fill="#2dd4bf"/>
  <circle cx="416" cy="103" r="3.5" fill="#2dd4bf"/>
  <circle cx="455" cy="119" r="3.5" fill="#2dd4bf"/>
  <circle cx="493" cy="131" r="3.5" fill="#2dd4bf"/>
  <circle cx="532" cy="141" r="3.5" fill="#2dd4bf"/>
  <circle cx="570" cy="164" r="3.5" fill="#2dd4bf"/>
  <text x="70" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">input</text>
  <text x="108" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">emb.</text>
  <text x="147" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">1</text>
  <text x="185" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">2</text>
  <text x="224" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">3</text>
  <text x="262" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">4</text>
  <text x="301" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">5</text>
  <text x="339" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">6</text>
  <text x="378" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">7</text>
  <text x="416" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">8</text>
  <text x="455" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">9</text>
  <text x="493" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">10</text>
  <text x="532" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">11</text>
  <text x="570" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">12</text>
  <text x="199" y="54" fill="#5eead4" font-size="12.5">layers 2–3: 0.90</text>
  <text x="570" y="186" fill="#fbbf24" font-size="12.5" text-anchor="end">output: 0.63</text>
  <text x="320" y="252" fill="#94a3b8" font-size="12" text-anchor="middle">Whisper encoder: input, embedding, then layers 1 to 12</text>
  <text x="16" y="120" fill="#94a3b8" font-size="12" text-anchor="middle" transform="rotate(-90 16 120)">how well pitch can be read (correlation)</text>
</svg>
<figcaption>Pitch read with a straight-line probe from each layer of Whisper's encoder, on singers the probe never saw. The melody is sharpest just after the input and fades towards the layer a language model would receive.</figcaption>
</figure>

**The melody is clearest right after the input and fades from there.** The read-out correlates 0.90 with the true pitch at layers 2 and 3, and 0.63 at the last layer, the one a language model would be given. An encoder trained to write down words has every reason to do this: pitch is what it must ignore to recognise the same word from two different speakers.

A correlation does not say whether what is left is still a usable melody, so I ran the song search again, three times, changing only where the contour comes from.

<figure class="mel-fig">
<svg viewBox="0 0 600 200" role="img" aria-label="The same song search names 56 of 120 hums from the real pitch, 62 from pitch read at layer 3 of the encoder, 34 from pitch read at its output, and the full voice model names 11; chance is 15">
  <text x="260" y="36" fill="#e2e8f0" font-size="12.5" text-anchor="end">Real pitch of the recording</text>
  <rect x="270" y="22" width="126" height="20" fill="#2dd4bf"/>
  <text x="403" y="37" fill="#e2e8f0" font-size="12.5">56</text>
  <text x="260" y="70" fill="#e2e8f0" font-size="12.5" text-anchor="end">Pitch read from encoder layer 3</text>
  <rect x="270" y="56" width="140" height="20" fill="#2dd4bf"/>
  <text x="417" y="71" fill="#e2e8f0" font-size="12.5">62</text>
  <text x="260" y="104" fill="#e2e8f0" font-size="12.5" text-anchor="end">Pitch read from the encoder output</text>
  <rect x="270" y="90" width="76" height="20" fill="#f59e0b"/>
  <text x="353" y="105" fill="#e2e8f0" font-size="12.5">34</text>
  <text x="260" y="138" fill="#e2e8f0" font-size="12.5" text-anchor="end">Full voice model (gpt-realtime-2.1)</text>
  <rect x="270" y="124" width="25" height="20" fill="#64748b"/>
  <text x="313" y="139" fill="#e2e8f0" font-size="12.5">11</text>
  <line x1="304" y1="14" x2="304" y2="158" stroke="#f59e0b" stroke-dasharray="5 4" stroke-width="2"/>
  <text x="310" y="174" fill="#fbbf24" font-size="12">chance: 15</text>
</svg>
<figcaption>Songs found by the same search, changing only where the melody is read from. Half of it is gone by the encoder's output; a full voice model uses none of what is left.</figcaption>
</figure>

**Half of the melody survives the encoder, and the full model uses none of it.** Read from layer 3, the contour finds 62 of 120 songs, slightly better than the pitch tracker's own 56. Read from the output, it finds 34, well above the 15 of chance. The complete voice model finds 11.

So there are two losses. Part of the melody is worn away inside the encoder, and what remains is not picked up afterwards. A recent benchmark, [SonicBench](https://arxiv.org/abs/2601.11039), reports the second half of this for basic properties of sound: frozen encoders still carry them while the full models answer near chance, and its authors place the bottleneck in the stages after the encoder. On hums, I see both.

The limits here matter. Whisper is OpenAI's open encoder, not necessarily the one inside `gpt-realtime-2.1` or ChatGPT's voice mode. I probed its small version, on 120 hums, and a straight-line probe gives a floor: a richer read-out might recover more from the last layer.

## What I take from it

**A model that hears is not the same as a model that listens for everything.** A speech model keeps what it was trained to keep. For melody, the working answer today is the one from thirty years ago, wrapped as a tool: extract the contour, search a catalogue, let the language model do the talking.

I would reach for the same pattern before assuming a voice model hears anything else that is not words: how fast someone speaks, whether they hesitate, whether the line dropped. Measure it first, and if it is not there, a small specialised listener next to the model is cheap.

Two things stay open, and each deserves its own piece. The first is what 46 % means. I do not know how a person would score on these same hums, and I suspect the answer turns on familiarity more than on hearing: whether you know the song at all, whether you know it but not its name, which passage was hummed. A Beatles melody I would probably get; one I have heard a handful of times, maybe not. The second is the search tool itself. Eight songs is a toy. Finding a contour among millions of tracks, quickly, with a notion of similarity that survives a bad singer, is a field of its own.

Everything here is on one corpus of eight songs, with one voice model per company and my own minimal search. It shows where to look, not how large the gap is in general.
