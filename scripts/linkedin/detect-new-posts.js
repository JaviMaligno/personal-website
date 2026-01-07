import { execSync } from 'child_process';
import { readFileSync, existsSync } from 'fs';
import matter from 'gray-matter';
import { setOutput } from './utils.js';

/**
 * Detects new or modified English blog posts from git diff
 * Outputs: has_new_posts, post_path, post_title
 */
async function detectNewPosts() {
  try {
    console.log('📝 Detecting new blog posts...');

    // Get changed files between commits
    const beforeCommit = process.env.GITHUB_BEFORE || 'HEAD~1';
    const afterCommit = process.env.GITHUB_AFTER || 'HEAD';

    console.log(`🔍 Comparing ${beforeCommit}...${afterCommit}`);

    const changedFiles = execSync(
      `git diff --name-status ${beforeCommit} ${afterCommit}`,
      { encoding: 'utf-8' }
    ).trim().split('\n');

    console.log(`Found ${changedFiles.length} changed files`);

    // Filter for new/modified English blog posts
    const newPosts = changedFiles
      .filter(line => {
        if (!line) return false;

        const [status, file] = line.split('\t');
        const isNewOrModified = (status === 'A' || status === 'M');
        const isEnglishBlogPost = file && file.startsWith('src/content/blog/en/') && file.endsWith('.md');

        if (isNewOrModified && isEnglishBlogPost) {
          console.log(`  ✅ ${status} ${file}`);
        }

        return isNewOrModified && isEnglishBlogPost;
      })
      .map(line => line.split('\t')[1]);

    if (newPosts.length === 0) {
      console.log('ℹ️  No new English blog posts detected');
      setOutput('has_new_posts', 'false');
      return;
    }

    // Process the first new post (if multiple, only publish the first)
    const postPath = newPosts[0];
    console.log(`\n📄 New post detected: ${postPath}`);

    if (newPosts.length > 1) {
      console.log(`⚠️  Multiple posts detected, processing only the first one:`);
      newPosts.forEach((post, index) => {
        console.log(`  ${index + 1}. ${post}`);
      });
    }

    // Read frontmatter
    if (!existsSync(postPath)) {
      throw new Error(`Post file not found: ${postPath}`);
    }

    const content = readFileSync(postPath, 'utf-8');
    const { data: frontmatter } = matter(content);

    console.log(`\nPost details:`);
    console.log(`  Title: ${frontmatter.title}`);
    console.log(`  Description: ${frontmatter.description?.substring(0, 100)}...`);
    console.log(`  Tags: ${frontmatter.tags?.join(', ')}`);
    console.log(`  LinkedIn Image: ${frontmatter.linkedinImage || 'None'}`);

    // Set outputs for next steps
    setOutput('has_new_posts', 'true');
    setOutput('post_path', postPath);
    setOutput('post_title', frontmatter.title);

    console.log('\n✅ Post detection complete');

  } catch (error) {
    console.error('❌ Error detecting new posts:', error.message);
    setOutput('has_new_posts', 'false');
    process.exit(1);
  }
}

detectNewPosts();
