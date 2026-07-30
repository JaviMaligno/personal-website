# Fuente: conversación con ChatGPT sobre sesgo del juez en LLM-as-a-judge

Conversación original: https://chatgpt.com/share/6a689657-8c00-83eb-9dca-fd976dda5c86
(el enlace compartido no es accesible de forma automatizada — Cloudflare devuelve 403 — así que
el texto está transcrito aquí.)

Tema: si el modelo o la familia de modelos que usas como juez introduce sesgo, especialmente en
tareas subjetivas. Sirve de base para un artículo secuela de `llm-as-judge-three-decisions`
(aquel cubre *qué* puntúas: contexto, unidad, dimensión; este cubre *quién* puntúa).

---

# Pregunta inicial

When it comes to LLM as a judge, I was thinking whether the model or family of model that you use as a judge would be relevant or would have a bias. For instance, I'm thinking particularly things that are a bit more subjective, because let's say you're judging an Anthropic model and an OpenAI model with an LLM as a judge. Obviously, if we're judging end products and it doesn't know where it comes from, let's say there's some code or frontend or something like that, images, assuming that's very agnostic, you would say, okay, it doesn't know who did it, so it should be unbiased. But even in those cases, and even more so when it comes about writing text, for instance, or things that are a little bit more subjective things, I think it's possible that a model from the same family, even if it's not the same, but if it's the same model precisely, then maybe even more so, would recognize the style. So when I say frontend, it may even recognize typical styles, or images, typical model images, and so on. So I don't know if there's any standard studies or benchmark for this, which models work better, which ones are more unbiased or more biased for judging if there is a standard of using judges from different models, again, which kind of task makes this more relevant or what task are usually similar across families, and so on. Again, also inside these families, maybe some models are more biased than others. What is the state of the art and standard for this?

---

# Respuesta

This is a very active area of research, and the short answer is: yes, the choice of judge matters a lot. In fact, one of the biggest findings over the last couple of years is that LLM-as-a-judge is not model-independent. Judges exhibit several systematic biases, including some that align with exactly the intuitions you describe.

It's useful to separate different kinds of bias.

## 1. Self-enhancement or "in-group" bias

This is probably the one you're thinking about.

Suppose you compare outputs from GPT and Claude, and you use GPT as the judge.

The concern is not necessarily that GPT explicitly recognizes "this was produced by Claude." Usually it doesn't have that information. Rather, the concern is that:

- GPT has preferences that are similar to its own training objectives.
- Claude has preferences that are similar to Anthropic's training objectives.
- Therefore GPT may systematically reward outputs that look "GPT-like."

Researchers sometimes call this self-preference or self-enhancement bias.

What's interesting is that this has actually been measured.

Several papers have found that models tend to rate outputs from their own family more highly, even when identities are hidden. The effect isn't always enormous, but it is statistically significant in many settings.

## 2. Style bias

This is actually a broader issue.

Different model families have fairly recognizable writing styles.

For example (oversimplifying):

- Claude often produces more structured, careful explanations.
- GPT models often optimize for clarity and directness.
- Gemini sometimes favors concise summaries.
- Llama-derived models often have slightly different discourse patterns.

Even if the judge doesn't literally identify the model, it may implicitly prefer one style over another because that style resembles what it learned to produce.

This becomes especially problematic for:

- creative writing
- essays
- marketing copy
- conversational responses
- long explanations

where there isn't a single objectively correct answer.

## 3. Position bias

This is one of the oldest known biases.

Suppose you ask

> Output A vs Output B

Many judges systematically prefer whichever answer appears first.

This is why nearly every serious evaluation now randomizes presentation order.

This bias exists regardless of model family.

## 4. Length bias

Another classic.

LLMs often equate

> longer = more complete = better

even when the longer answer is actually worse.

So if Claude tends to answer in 800 words and GPT in 500 words, an LLM judge may over-reward Claude simply because it looks more comprehensive.

This has been repeatedly observed.

## 5. Verbosity and confidence bias

Related to length.

Models often prefer answers that sound:

- confident
- polished
- authoritative

even when they're factually wrong.

Human judges also suffer from this, so it's not unique to LLMs.

## Can judges recognize specific model families?

Interestingly, yes.

Not perfectly. But better than chance.

Several studies have shown that both humans and LLMs can often identify GPT outputs, Claude outputs and Gemini outputs with fairly high accuracy.

This happens because models have:

- preferred formatting
- preferred vocabulary
- preferred hedging
- characteristic reasoning structure

So your intuition that a GPT judge might subconsciously recognize GPT outputs isn't crazy at all. It doesn't need explicit identification.

## Does this matter equally for every task?

No. This is probably the biggest distinction.

### Low-subjectivity tasks

Examples: factual QA, math, code correctness, passing unit tests, JSON validity, schema adherence.

Here the judge matters much less.

Often the best judge is actually not an LLM, but an executable verifier: compiler, unit tests, symbolic checker, theorem prover.

If an LLM is used, different judge families tend to agree much more.

### Medium-subjectivity tasks

Examples: summarization, instruction following, document QA, extraction.

Judges still differ, but agreement is reasonably high.

### High-subjectivity tasks

This is where things become difficult.

Examples: creative writing, marketing, storytelling, UX copy, educational explanations, frontend aesthetics, image quality, tone, helpfulness.

Here judge choice can completely change rankings. This is why leaderboards on these tasks should be interpreted carefully.

## What about frontend?

Frontend is actually an interesting case.

Suppose two models independently build a React application.

Even if the judge only sees screenshots, it might still learn preferences for things like: whitespace, component hierarchy, typography, Tailwind conventions, color palettes, button sizing, animation style.

Some model families consistently generate similar UI aesthetics. So yes, there can absolutely be family effects.

This is one reason recent UI benchmarks often combine screenshot evaluation, functional evaluation, human preference and interaction tests, rather than relying on one judge.

## What is the current best practice?

The community has gradually converged on several techniques.

1. **Use multiple judges.** Instead of "GPT judges everyone", people increasingly use GPT + Claude + Gemini and aggregate the scores. This dramatically reduces family-specific bias.
2. **Pairwise comparison.** Rather than giving each output a score from 1–10, ask "Which answer is better?" Pairwise comparisons are generally much more stable than absolute ratings.
3. **Randomize answer order.** Always randomize A/B versus B/A to eliminate position bias.
4. **Calibrate against humans.** The most common metric is no longer "Does GPT agree with GPT?" Instead it's "How well does this judge correlate with expert human preferences?" This is sometimes called judge alignment.
5. **Ensemble judges.** Many evaluations now average across several judges. This tends to produce rankings that are much more robust.

## Is there a "best" judge?

Not really.

Historically, newer frontier models have tended to correlate better with human preferences than older or smaller models, but there is no universally unbiased judge. A model that excels at judging coding solutions may be less reliable for evaluating persuasive writing or creative work.

In recent evaluations, strong frontier models from OpenAI, Anthropic, and Google have all been used as judges, but researchers increasingly avoid treating any single one as a gold standard. Instead, they compare agreement with humans and with other judges.

## Where is the field heading?

One emerging idea is that evaluation should itself be an ensemble problem. Instead of asking "Which model is the best judge?", researchers ask "How can we combine diverse judges to minimize systematic error?"

Current directions include:

- **Panel-of-judges** approaches, where multiple LLMs vote or deliberate before producing a verdict.
- **Specialized judges** trained or prompted for particular domains (e.g., code, legal writing, UX, safety) rather than one general-purpose evaluator.
- **Judge calibration**, where judges are periodically benchmarked against expert human annotations and adjusted if they systematically over- or under-rate certain styles.
- **Adversarial evaluation**, in which models are tested on examples specifically designed to expose biases such as verbosity preference, self-preference, or susceptibility to persuasive but incorrect reasoning.

Overall, the consensus is shifting away from the idea that there exists a single objective LLM judge. Instead, researchers increasingly treat judges much like human evaluators: each has strengths, weaknesses, and preferences. For objective tasks, automated verifiers or execution-based metrics are preferred whenever possible. For subjective tasks, the most reliable evaluations combine multiple independent judges, randomize presentation, use pairwise comparisons, and validate the resulting rankings against human preferences. Your intuition — that a judge may implicitly recognize and favor outputs resembling its own family even without explicit provenance — is well supported by the current literature and is now considered one of the central methodological issues in LLM evaluation.

---

# Notas para el artículo

- Las afirmaciones sobre estudios concretos vienen sin cita. **Verificar antes de publicar**
  (MT-Bench / Zheng et al. 2023 para position y self-enhancement bias; trabajos posteriores
  sobre self-preference y length bias). No repetir "varios papers han encontrado" sin fuente.
- El ángulo diferencial frente a un resumen: **medir el delta de auto-preferencia**, no la tasa
  bruta. Que un juez prefiera su propio output no prueba sesgo si ese output es simplemente
  mejor; lo que lo prueba es que lo prefiera *más que los otros jueces sobre el mismo par*.
- Ver `experiments/judge-bias/` para el harness y los resultados del piloto.
