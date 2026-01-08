# 🚀 Dev.to Quick Start Guide

Get your Dev.to automation running in 5 minutes.

## Step 1: Get Your Dev.to API Key (2 min)

1. **Sign up/Login to Dev.to:**
   - Go to https://dev.to
   - Sign up with GitHub (fastest) or email

2. **Generate API Key:**
   - Visit: https://dev.to/settings/extensions
   - Scroll to **"DEV Community API Keys"**
   - Click **"Generate API Key"**
   - Name it: `Personal Website Publisher`
   - **Copy the key** (you won't see it again!)

3. **Save it temporarily:**
   ```bash
   # In your terminal:
   export DEVTO_API_KEY="your_key_here"
   ```

---

## Step 2: Test with an Existing Post (1 min)

Pick one of your existing posts to test:

```bash
# Option 1: MCP Server Bitbucket (recommended for first test)
npm run test:devto mcp-server-bitbucket.md

# Option 2: Claude Code Skills
npm run test:devto claude-code-skills-blog-writer.md

# Option 3: Parallel AI Agents
npm run test:devto parallel-ai-agent-development.md

# Option 4: TypeScript Guardrails
npm run test:devto typescript-ai-agent-guardrails.md

# Option 5: Azure Content Filter
npm run test:devto azure-content-filter-workarounds.md
```

Expected output:
```
✅ Successfully published to Dev.to!

📍 Dev.to Draft URL: https://dev.to/yourname/building-an-mcp-server-1234
🆔 Article ID: 12345
```

---

## Step 3: Review Your Draft (1 min)

1. Click the URL from the output
2. Check:
   - ✅ Title looks good
   - ✅ Content renders properly (code blocks, headings, etc.)
   - ✅ Tags are present (bottom of post)
   - ✅ Canonical URL is shown (prevents duplicate content)
   - ✅ CTA link to your portfolio is at the end

---

## Step 4: Publish or Edit

**Option A - Publish immediately:**
- Click **"Publish"** button on Dev.to

**Option B - Edit first:**
- Click **"Edit"**
- Adjust anything you want
- Add a better cover image (optional)
- Then **"Publish"**

**Option C - Keep as draft:**
- Leave it for now
- Publish later when you're ready

---

## Step 5: Add API Key to GitHub (1 min)

So it works automatically for new posts:

1. Go to: https://github.com/JaviMaligno/personal-website/settings/secrets/actions

2. Click **"New repository secret"**

3. Fill in:
   - **Name:** `DEVTO_API_KEY`
   - **Secret:** Paste your Dev.to API key

4. Click **"Add secret"**

✅ Done! Now every new blog post will auto-publish to Dev.to as a draft.

---

## Testing Results

After testing 1-2 posts, check:

### ✅ Success indicators:
- Draft appears on Dev.to
- Canonical URL points to your blog
- Code blocks render correctly
- Tags are applied
- CTA link works

### ⚠️ If something's wrong:
- **401 error**: API key is invalid - regenerate it
- **422 error**: Check tags are lowercase, max 4
- **Image missing**: That's OK, add one manually on Dev.to
- **Formatting issues**: Edit the draft on Dev.to directly

---

## What to Publish First

**Recommendation: Start with these 2:**

1. **MCP Server Bitbucket** - Your most technical/impressive post
   ```bash
   npm run test:devto mcp-server-bitbucket.md
   ```

2. **Claude Code Skills** - Relevant to Dev.to audience (many use Claude)
   ```bash
   npm run test:devto claude-code-skills-blog-writer.md
   ```

**Why these?**
- Both are technical and practical
- Dev.to audience loves AI/developer tools content
- Good examples of your expertise
- Will likely get engagement (comments, likes)

---

## Next Steps After Testing

Once you've successfully published 1-2 posts:

### 1. Configure Your Dev.to Profile

**Bio suggestion:**
```markdown
AI Agent Architect building multi-agent systems and MCP servers.

I write about:
• Multi-agent orchestration patterns
• Model Context Protocol (MCP) development
• AI compliance automation
• Real-world AI agent architectures

Portfolio: https://www.javieraguilar.ai
```

**Photo:** Use your Hopf fibration (consistent with GitHub)

### 2. Engage with the Community

- Respond to comments on your posts
- Comment on other AI/agent posts
- Join discussions with tags: `#ai`, `#claude`, `#mcp`

### 3. Write New Content

When you publish a new post to your blog:
1. Push to GitHub → Auto-publishes to Dev.to as draft
2. Review draft on Dev.to
3. Publish when ready

---

## Troubleshooting

### "Command not found: npm"
You need Node.js installed. Already have it, just run from the repo directory.

### "DEVTO_API_KEY is required"
```bash
export DEVTO_API_KEY="your_key_here"
```

### "File not found"
Make sure you're in the repo root directory:
```bash
cd /Users/javieraguilarmartin1/Documents/repos/personal-website
```

### Want to test more posts?
```bash
# Test all 5 posts (one by one):
npm run test:devto mcp-server-bitbucket.md
npm run test:devto claude-code-skills-blog-writer.md
npm run test:devto parallel-ai-agent-development.md
npm run test:devto typescript-ai-agent-guardrails.md
npm run test:devto azure-content-filter-workarounds.md
```

---

## Full Documentation

For detailed info, see: `scripts/devto/README.md`

---

**Ready to start?** Run the first test command! 🚀
