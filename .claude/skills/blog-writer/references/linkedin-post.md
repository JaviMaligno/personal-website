# The LinkedIn feed post (`linkedinSummary`)

The post that goes out when an article is published is the `linkedinSummary`
field of the EN frontmatter, verbatim. Nothing generates it any more: until
2026-11-14 a Gemini summary filled the gap, and that day it published a post
whose first sentence nobody could parse. Writing it here, in the article PR,
is the point: it gets the same care and review as the article.

## Who it is for

Not people who want to know about my product or my experiment. People who want
to know about AI, and who should recognise their own work in the post. The
article can be about one service, one pipeline, one measurement; the post is
about the lesson that travels beyond it.

So before writing, answer one question: **what is the general case?** What
would a reader who has never heard of this project take into their own work?
For a pipeline nobody used, it is not "my pipeline failed": it is that people
who already work inside an agent want the tool brought to the agent, which
often means a plugin rather than another application.

## How to build it

- **Open with the general lesson or a situation the reader recognises**, not
  with the product's name or the experiment's setup. The first line stands on
  its own: LinkedIn cuts at about 200 characters with "see more".
- **The specific case is the evidence, not the story.** One or two concrete
  details that make the lesson believable: the number that carries the point,
  the moment it went wrong. Leave the method, the arms, the model versions and
  the internal names in the article unless the lesson needs them.
- **Connect it to the wider conversation.** If other articles of mine make the
  same argument, say so in a sentence and link them through `linkedinLinks`
  (`{ label, url }`, rendered as `🔗 <label>: <url>`). The same goes for the
  external work the article answers. A lesson that shows up in several places
  is more convincing than one anecdote.
- **Close with what the reader can do or ask** in their own work: the
  question to ask before building, the check to run, the rule of thumb.
- **No stronger than the article.** The post can generalise the lesson, but
  every claim and number must hold in the article, with its scope.

## Form

- Five to seven short paragraphs. First person, spoken tone, same voice as the
  article (see `voice-and-sources.md`).
- No URLs and no hashtags in the text: the article link, `repoUrl`,
  `linkedinLinks` and the tags are appended automatically
  (`buildPostText` in `scripts/linkedin/utils.js`).
- YAML `|` block in the EN frontmatter only.

## Review

Show the post to Javier with the article preview, as text he can read on its
own. `scheduled-publish.yml` refuses to merge an article without it, so a
missing post blocks the publication instead of going out unwritten.
