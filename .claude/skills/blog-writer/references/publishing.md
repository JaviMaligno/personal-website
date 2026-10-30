# Publishing and scheduling

The whole mechanism (manifest, cron, merge driver, cross-posts) is in `docs/blog-publishing.md` and
the repo's `CLAUDE.md`; read them before choosing or moving a date. This file holds the order of
the steps and what goes with the article.

## Order of the steps

1. **Content final.** Javier has reviewed the rendered pages and every correction is in. The
   article branch holds only that article's files (`gh pr diff`).
2. **Website date.** An entry in `.github/publish-schedule.json` on `main` (slug, branch, article,
   date), and the same `pubDate` in EN and ES. A reactive article (answering a tweet, a paper, a
   current event) takes the first free date; the rest follow the cadence. One article at a time,
   each merged on Javier's explicit signal.
3. **Video on the same day.** The article's reel goes out the day the article does; a part 2 goes
   the next day, since two reels on one day compete. Everything not yet published can be
   reordered to make room, except today's reel; a reel never goes out before its article. The
   video itself is made with the `article-video` skill and scheduled with `schedule-social-video`
   (AGILabs video studio plugin).
4. **Native LinkedIn article, last.** Once the content is final, following
   [linkedin-articles.md](linkedin-articles.md): by default the day after the website, at 9:00. A
   scheduled native article cannot be edited, so it is the last thing to set.
5. **X.** When the article answers a tweet, prepare the reply or quote: say which one it is, give
   the exact tweet URL, the text counted under 280 characters, and the article link.

## On the publication day

The cron lands the article on `main` in the afternoon or evening UTC. That day, check that the page
is live (`https://www.javieraguilar.ai/en/blog/<slug>/` answers 200) before the native article's
time. If it is not, look at the `scheduled-publish.yml` run first: an expired `PUBLISH_PAT` stops
the push silently, and the native article then links to a 404.

## Editing after publication

`detect-new-posts.js` only picks up added files, so an edit produces no duplicate LinkedIn post and
also never reaches Dev.to: re-run `devto-post.yml` with `post_path=src/content/blog/en/<slug>.md`.
The original LinkedIn feed post has no automatic fix.

## Video Embeds

Use HTML iframe embeds for video platforms. The website supports full HTML.

**Loom example:**
```html
<div style="position: relative; padding-bottom: 56.25%; height: 0;">
  <iframe src="https://www.loom.com/embed/VIDEO_ID"
          frameborder="0"
          webkitallowfullscreen
          mozallowfullscreen
          allowfullscreen
          style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">
  </iframe>
</div>
```

**YouTube example:**
```html
<div style="position: relative; padding-bottom: 56.25%; height: 0;">
  <iframe src="https://www.youtube.com/embed/VIDEO_ID"
          frameborder="0"
          allowfullscreen
          style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">
  </iframe>
</div>
```

### Dev.to Compatibility

**Important:** Dev.to filters HTML iframes for security. The publish script (`scripts/devto/publish-to-devto.js`) automatically transforms video embeds:

- **Loom iframes** → Markdown links with note
- **YouTube iframes** → Could be transformed to `{% youtube %}` liquid tags (not implemented yet)

**What gets sent to Dev.to:**
```markdown
**🎥 [Watch the video demo on Loom](https://www.loom.com/share/VIDEO_ID)**

> _Note: Interactive video player available on the [original article](CANONICAL_URL)_
```

**Best Practice:**
- Always use iframe embeds in the markdown
- The Dev.to publish script handles the transformation automatically
- Don't manually create different versions for Dev.to
