# Dev.to Publishing Automation

Automatically publishes blog posts to Dev.to when you push new content to your blog.

## Features

- ✅ **Automatic publishing** - New blog posts are auto-published to Dev.to as drafts
- ✅ **Canonical URLs** - Prevents duplicate content penalties
- ✅ **CTA injection** - Automatically adds portfolio link at the end
- ✅ **Tag support** - Uses up to 4 tags from frontmatter
- ✅ **Cover images** - Uses your OG image or custom cover
- ✅ **Test script** - Publish existing posts for testing

## Setup

### 1. Create Dev.to Account

If you don't have one:
1. Go to https://dev.to
2. Sign up (can use GitHub authentication)

### 2. Get API Key

1. Go to https://dev.to/settings/extensions
2. Scroll to "DEV Community API Keys"
3. Click "Generate API Key"
4. Give it a name (e.g., "Personal Website Auto-Publisher")
5. Copy the API key (you'll only see it once!)

### 3. Add Secret to GitHub

1. Go to your repo: https://github.com/JaviMaligno/personal-website
2. **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Name: `DEVTO_API_KEY`
5. Value: Paste your Dev.to API key
6. Click **"Add secret"**

### 4. Update Your Profile (Optional)

Configure your Dev.to bio using the recommendations from earlier:

```markdown
AI Agent Architect building multi-agent systems and MCP servers.

I write about:
• Multi-agent orchestration patterns
• Model Context Protocol (MCP) development
• AI compliance automation
• Real-world AI agent architectures

Portfolio: https://www.javieraguilar.ai
```

## Usage

### Automatic Publishing (New Posts)

Just push a new blog post to `src/content/blog/en/*.md`:

```bash
git add src/content/blog/en/my-new-post.md
git commit -m "Add new post about..."
git push origin main
```

The GitHub Action will:
1. Detect the new post
2. Publish it to Dev.to as a **DRAFT**
3. You get a notification with the Dev.to URL
4. Review and publish manually on Dev.to

### Publishing Existing Posts (Testing)

To test with your existing articles:

```bash
# Set your API key
export DEVTO_API_KEY="your_api_key_here"

# Publish a specific post
node scripts/devto/publish-existing-post.js mcp-server-bitbucket.md

# Or try another one
node scripts/devto/publish-existing-post.js claude-code-skills-blog-writer.md
```

**Available posts:**
- `azure-content-filter-workarounds.md`
- `claude-code-skills-blog-writer.md`
- `mcp-server-bitbucket.md`
- `parallel-ai-agent-development.md`
- `typescript-ai-agent-guardrails.md`

### Controlling Publication

Add these optional fields to your post's frontmatter:

```yaml
---
title: "Your Post Title"
description: "Post description"
tags: ["ai", "agents", "claude", "mcp"]  # Max 4 tags
publishToDevto: true   # Set to false to skip Dev.to
devtoPublished: false  # true = publish immediately, false = draft
coverImage: "/path/to/custom-image.png"  # Optional custom cover
---
```

## What Gets Published

### Content Transformation

Your Markdown is published as-is, with these additions:

**At the end of each post:**
```markdown
---

*Originally published on [javieraguilar.ai](canonical-url)*

Want to see more AI agent projects? Check out my [portfolio](https://www.javieraguilar.ai)
where I showcase multi-agent systems, MCP development, and compliance automation.
```

### Metadata Mapping

| Your Blog | Dev.to |
|-----------|--------|
| `title` | Article title |
| `description` | Article description |
| `tags` (first 4) | Article tags |
| `coverImage` or OG image | Cover image |
| Blog URL | Canonical URL |

## Testing Your Setup

### Test 1: Publish an Existing Post

```bash
export DEVTO_API_KEY="your_key_here"
node scripts/devto/publish-existing-post.js mcp-server-bitbucket.md
```

Expected output:
```
✅ Successfully published to Dev.to!
📍 Dev.to Draft URL: https://dev.to/yourname/building-an-mcp-server-1234
```

### Test 2: Check the Draft

1. Visit the URL from the output
2. Verify:
   - ✅ Title is correct
   - ✅ Content renders properly
   - ✅ Code blocks format correctly
   - ✅ Tags are present
   - ✅ Canonical URL points to your blog
   - ✅ CTA is at the bottom

### Test 3: Publish It

1. On Dev.to draft page, click **"Edit"** if needed
2. Review everything
3. Click **"Publish"** when ready

## Troubleshooting

### "DEVTO_API_KEY is required"

Make sure you:
1. Generated the API key on Dev.to
2. Added it as a GitHub secret (for automatic publishing)
3. Or exported it as environment variable (for manual testing)

### "Dev.to API error (401)"

Your API key is invalid or expired. Generate a new one at https://dev.to/settings/extensions

### "Dev.to API error (422)"

Usually means:
- Tags are invalid (use lowercase, no spaces)
- Title is too long (max 60 chars recommended)
- Content has formatting issues

### Tags Don't Appear

Dev.to only allows 4 tags maximum. If your post has more, only the first 4 are used.

### Image Doesn't Show

Make sure your `coverImage` URL is:
- Publicly accessible (HTTPS)
- A direct image URL (not a page)
- Ideally 1000x420px for best display

## Best Practices

### 1. Always Review Drafts

Auto-publish creates **DRAFTS** by default. Always review on Dev.to before publishing.

### 2. Choose Good Tags

Popular Dev.to tags:
- `ai`, `machinelearning`, `python`, `javascript`, `typescript`
- `devops`, `api`, `tutorial`, `beginners`, `discuss`
- `claude`, `anthropic`, `llm` (smaller communities)

### 3. Optimize for Dev.to Audience

Dev.to readers prefer:
- **Code examples** - More code blocks than theory
- **Practical tutorials** - "How to" rather than "Why"
- **Clear structure** - Use H2/H3 headings
- **Inline explanations** - Comment your code

### 4. Engage with Comments

- Respond to comments on your Dev.to posts
- This increases visibility in Dev.to's algorithm
- Builds your reputation in the community

## Rate Limits

Dev.to API limits:
- **30 requests per 30 seconds**
- For this automation, you'll rarely hit this (1 request per new post)

## Workflow Architecture

```
GitHub Push (new post)
    ↓
detect-new-posts.js (reused from LinkedIn)
    ↓
publish-to-devto.js
    ↓
Dev.to API
    ↓
Draft Created ✅
    ↓
You review & publish manually
```

## Example: Full Workflow

1. **Write post:** `src/content/blog/en/my-awesome-post.md`

2. **Frontmatter:**
```yaml
---
title: "Building AI Agents That Actually Work"
description: "Practical guide to production-ready AI agents"
tags: ["ai", "agents", "tutorial", "claude"]
publishToDevto: true
devtoPublished: false  # Draft first
---
```

3. **Push to GitHub:**
```bash
git add src/content/blog/en/my-awesome-post.md
git commit -m "Add new post: Building AI Agents"
git push origin main
```

4. **GitHub Action runs** (check Actions tab)

5. **Check your email** - Dev.to sends notification when draft is created

6. **Review on Dev.to** - Visit the draft URL

7. **Publish** - Click "Publish" button on Dev.to

8. **Share** - Post link on LinkedIn, Twitter, etc.

## Next Steps

Once you've tested and it works:

1. ✅ Publish 1-2 existing posts to build presence
2. ✅ Engage with comments
3. ✅ Write new content optimized for Dev.to
4. ✅ Cross-promote between your blog and Dev.to
5. ✅ Track which posts get most engagement

## Resources

- [Dev.to API Docs](https://developers.forem.com/api/v0)
- [Dev.to Publishing Guide](https://dev.to/p/editor_guide)
- [Dev.to Tags](https://dev.to/tags)

---

**Questions?** Check the main documentation or create an issue.
