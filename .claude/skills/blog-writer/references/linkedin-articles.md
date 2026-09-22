# Native LinkedIn articles

The agent writing a blog article also creates its native LinkedIn article when
carrying out an authorized publication or scheduling task. Complete the browser
step in the same session; do not leave a copy-and-paste task for Javier when the
browser is available. Respect requests limited to drafts, reviews, or specific
channels. This workflow does not authorize publishing unrelated content.

## Relationship to the existing workflow

Read `docs/blog-publishing.md` before choosing dates. Merging the website article
triggers a brief LinkedIn feed post through `linkedin-post.yml`. Keep that path
and add the full native article through LinkedIn's article editor. The public
Posts API's `content.article` shares a link preview; it does not create the full
article body. Do not add a second API post as a substitute.

Use the EN article by default, matching the existing distribution language,
unless Javier specifies another language. The bilingual website does not imply
publishing two native LinkedIn articles.

## Prepare the article for the editor

- Adapt the reviewed full article, preserving its argument, examples, sources
  and useful code. Include a title, cover, headings and relevant inline figures.
- Use native editor formatting. Remove YAML frontmatter and website-only HTML,
  CSS and components; do not paste Markdown and assume it renders correctly.
- Upload the existing cover and figure assets. For inline SVG diagrams, use the
  pre-rendered PNGs, keeping captions and alt text where supported. Check that
  tables, code and video embeds remain readable; use a clear supported layout
  or link where necessary.
- Resolve relative links to public absolute URLs and add a link to the original
  website article. Verify the website is live before immediate publication. If
  scheduling ahead, use its verified canonical route and place the LinkedIn
  article after the website's planned release, allowing for cron delays.

## Publish or schedule through the browser

1. Load the available browser-control skill and use the signed-in session.
   Confirm Javier's personal profile is the selected author. Inspect existing
   drafts, scheduled articles and published articles for this title/topic and
   original URL; reuse the matching draft instead of creating duplicates.
2. Open **Write article**, choose an individual article, and fill the title,
   cover and full body. Do not create or enroll it in a newsletter unless asked.
3. Preview the rendered result. Check cover cropping, headings, all figures and
   captions, code, links, and the beginning and end of the body for truncation.
4. Honor the requested date. If no date is given and scheduling is authorized,
   prefer a free day after the website release and its automatic feed post.
   Check `.github/publish-schedule.json`, `scripts/linkedin/posts/schedule.json`
   and the visible LinkedIn schedule. Allow for the feed update accompanying
   the native article when avoiding multiple publications on the same day.
   Record the date and time the editor actually selected. Do not invent a fixed
   two-day offset.
5. Publish now or use the editor's native scheduling control, according to the
   authorized task. Set suitable introductory feed text without manually
   duplicating the existing automated post. These browser-scheduled articles
   are not tracked or collision-checked by the repository's API schedulers;
   do not add them to those queues as though the queues could publish them.
6. Verify the resulting live article and URL, or reopen the scheduled list and
   confirm the entry and selected time. A saved draft is not a scheduled article.
   Return the verified state and URL (if available) to Javier.

If a submission times out or its outcome is unclear, inspect published and
scheduled entries before retrying. If the session is unavailable, a login
challenge appears, or the editor cannot complete the action, preserve the draft
when possible and report the specific blocker. Do not claim success or create
another copy to work around an uncertain result.

## Editor mechanics (observed September 2026)

These notes come from building twelve native articles in one session. They
describe how the editor behaved then; confirm them against the current editor
before relying on them.

**Body.** The body is a ProseMirror editor (`.ProseMirror`). Building the text as
HTML and dispatching a `paste` event with a `DataTransfer` holding `text/html` is
far faster and more reliable than typing or using the Style menu. The paste
keeps links, bold, italics, lists, `<blockquote>` and `<pre><code>` blocks.
Heading levels shift down one: `<h1>` becomes the native "Heading" and `<h2>`
becomes "Subheading". Inline `<code>` survives but renders as plain text.
Paste in chunks that end where a figure goes. Before each paste, put the cursor
in an empty paragraph at the end of the document, or the first pasted paragraph
merges into the previous one.

**What does not survive.** There are no tables: rewrite each row as a list item
and fix any sentence that refers to "columns". There is no maths rendering:
write inline maths in Unicode (π, ρ, φ, ≤, subscripts) and put displayed
equations in a code block. Remove website-only HTML such as inline SVG; use the
pre-rendered figure PNGs.

**Figures.** No `input[type=file]` exists until the upload button runs, and the
native file picker is out of reach. Override `HTMLInputElement.prototype.click`
so that a file input is captured and attached to the DOM instead of opening the
picker. Then upload into it with the browser's file-upload tool, from files
copied into the session scratchpad. The image dialog has an ALT field, which
took about 450 characters without complaint. The caption is a textarea on the
inserted figure with `maxlength=250`, and it truncates silently. Rewrite longer
website captions to fit rather than letting them be cut.

**Code blocks.** Pressing Enter after a `<pre>` stays inside the code block, and
undo reverts the whole paste. When a chunk ends in a code block, end it with a
marker paragraph (for example `<p>@@</p>`). Select the marker text and delete
it, which leaves an empty paragraph after the block.

**Cover.** The cover is cropped to 16:9. A 2:1 hero with labels or panels near
its left or right edge loses them. Pad it with
[`scripts/pad_cover_16x9.py`](../scripts/pad_cover_16x9.py) and upload the padded
file, but look at the result before using it. Illustrations whose edges carry
nothing can go up unchanged. Large files (about 1.5 MB or more) take up to 20
seconds to process. Wait for the cover before clicking into the title, or the
typed title is lost.

**Autolinks.** The editor turns link-like text into links. The visible
`javieraguilar.ai/...` link text becomes an `http://` link that redirects
correctly. A bare filename such as `findings.md` becomes a link to
`http://findings.md`. After the last paste, list every `href` in the body and fix
any that the source article does not contain. The link dialog cannot remove a
link, so point it at the correct target instead.

**Scheduling.** Set the date and time before writing the introductory feed text,
because returning from the schedule dialog clears it. Scheduling reached about
three months ahead (the calendar stopped at 20 December from 22 September). The
schedule dialog shrinks after the calendar closes, so a click on its old
position can land outside it and open "Discard draft". Choose **Go back**.
The Scheduled list shows the first ten entries; use "Show more results" to
verify the rest.

## Platform references

- [Write, publish and schedule articles](https://www.linkedin.com/help/learning/answer/a522427)
- [Posts API: link sharing versus native articles](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api)

Inspect the current editor rather than relying on hard-coded selectors or old
screenshots; consult the official help if controls have changed.
