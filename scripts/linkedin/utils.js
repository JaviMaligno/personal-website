import { readFileSync, appendFileSync, statSync } from 'fs';

/**
 * Set GitHub Actions output
 * Writes output variables that can be used by subsequent workflow steps
 */
export function setOutput(name, value) {
  const outputFile = process.env.GITHUB_OUTPUT;
  if (outputFile) {
    appendFileSync(outputFile, `${name}=${value}\n`);
  }
  console.log(`::set-output name=${name}::${value}`);
}

/**
 * Upload image to LinkedIn
 * Returns: Image URN for use in post
 *
 * @param {string} imagePath - Local path to image file
 * @returns {Promise<string>} - LinkedIn asset URN
 */
export async function uploadImageToLinkedIn(imagePath) {
  const accessToken = process.env.LINKEDIN_ACCESS_TOKEN;
  const personUrn = process.env.LINKEDIN_PERSON_URN;

  try {
    console.log(`🤖 Step 1: Registering image upload...`);

    // Ensure personUrn is in full URN format
    const fullOwnerUrn = personUrn.startsWith('urn:li:person:')
      ? personUrn
      : `urn:li:person:${personUrn}`;

    // Step 1: Register upload
    const registerResponse = await fetch('https://api.linkedin.com/v2/assets?action=registerUpload', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0',
      },
      body: JSON.stringify({
        registerUploadRequest: {
          recipes: ['urn:li:digitalmediaRecipe:feedshare-image'],
          owner: fullOwnerUrn,
          serviceRelationships: [{
            relationshipType: 'OWNER',
            identifier: 'urn:li:userGeneratedContent',
          }],
        },
      }),
    });

    if (!registerResponse.ok) {
      const errorText = await registerResponse.text();
      throw new Error(`Image registration failed (${registerResponse.status}): ${errorText}`);
    }

    const registerData = await registerResponse.json();
    const uploadUrl = registerData.value.uploadMechanism['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest'].uploadUrl;
    const asset = registerData.value.asset;

    console.log(`🤖 Step 2: Uploading image binary...`);

    // Step 2: Upload image binary
    const imageBuffer = readFileSync(imagePath);

    const uploadResponse = await fetch(uploadUrl, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/octet-stream',
      },
      body: imageBuffer,
    });

    if (!uploadResponse.ok) {
      const errorText = await uploadResponse.text();
      throw new Error(`Image upload failed (${uploadResponse.status}): ${errorText}`);
    }

    console.log(`✅ Image uploaded successfully: ${asset}`);
    return asset;

  } catch (error) {
    console.error('❌ Error uploading image to LinkedIn:', error.message);
    throw error;
  }
}

/**
 * Parse @-mentions from raw post text.
 *
 * Syntax in .txt files: @[Visible Name](urn:li:organization:1337)
 *                       @[Person Name](urn:li:person:abc123)
 *
 * The marker is removed from the text (only "Visible Name" remains) and
 * start/length offsets are computed over the CLEANED text.
 *
 * IMPORTANT (offsets): LinkedIn counts start/length over the final text.
 * JavaScript strings are UTF-16, so `.length`/index arithmetic here is in
 * UTF-16 code units — emojis outside the BMP (🚀, 🤖, …) count as 2 units.
 * This matches LinkedIn's observed behavior. Do NOT recompute offsets with
 * grapheme- or codepoint-based counting.
 *
 * NOTE: LinkedIn only renders the mention as a link if the visible text
 * matches the real name of the company/person (case-sensitive). Otherwise
 * it falls back to plain text.
 *
 * @param {string} rawText - Text possibly containing @[Name](urn) markers
 * @returns {{ text: string, mentions: Array<{start: number, length: number, name: string, urn: string}> }}
 */
export function parseMentions(rawText) {
  const MENTION_REGEX = /@\[([^\]]+)\]\((urn:li:(?:organization|person):[^)\s]+)\)/g;
  const mentions = [];
  let cleanText = '';
  let lastIndex = 0;

  for (const match of rawText.matchAll(MENTION_REGEX)) {
    cleanText += rawText.slice(lastIndex, match.index);
    const [marker, name, urn] = match;
    mentions.push({
      start: cleanText.length,   // UTF-16 code units (see note above)
      length: name.length,       // UTF-16 code units
      name,
      urn,
    });
    cleanText += name;
    lastIndex = match.index + marker.length;
  }
  cleanText += rawText.slice(lastIndex);

  return { text: cleanText, mentions };
}

/**
 * Build shareCommentary.attributes from parsed mentions.
 * Companies use CompanyAttributedEntity, people use MemberAttributedEntity.
 * Ref: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/ugc-post-api (Attribute schema)
 *
 * @param {Array<{start: number, length: number, urn: string}>} mentions
 * @returns {Array<Object>} - Attributes array for shareCommentary
 */
export function buildMentionAttributes(mentions = []) {
  return mentions.map(({ start, length, urn }) => ({
    start,
    length,
    value: urn.startsWith('urn:li:organization:')
      ? { 'com.linkedin.common.CompanyAttributedEntity': { company: urn } }
      : { 'com.linkedin.common.MemberAttributedEntity': { member: urn } },
  }));
}

/**
 * Compose the LinkedIn post text (pure function — used by the publisher and tests).
 * Layout: summary, then an optional "💻 Code" line when repoUrl is set, then the
 * "📖 Read more" link, then hashtags. Truncates the summary to keep the whole post
 * under maxLength characters (LinkedIn's limit is 3000).
 *
 * @param {Object} p
 * @param {string} p.summary   - Generated summary body
 * @param {string} p.postUrl   - Canonical article URL
 * @param {string} [p.hashtags] - Space-joined hashtags line
 * @param {string} [p.repoUrl]  - Optional code repo URL
 * @param {number} [p.maxLength] - Character cap (default 3000)
 * @returns {string} the final post text
 */
export function buildPostText({ summary, postUrl, hashtags = '', repoUrl = '', maxLength = 3000 }) {
  const repoLine = repoUrl ? `💻 Code: ${repoUrl}\n` : '';
  const compose = (body) => `${body}\n\n${repoLine}📖 Read more: ${postUrl}\n\n${hashtags}`;
  let postText = compose(summary);
  if (postText.length > maxLength) {
    const maxSummaryLength = maxLength - postUrl.length - repoLine.length - hashtags.length - 50;
    postText = compose(summary.substring(0, Math.max(0, maxSummaryLength)) + '...');
  }
  return postText;
}

/**
 * Build the ugcPosts request body (pure function — used by dry-run and tests).
 *
 * @param {Object} params - Same params as createLinkedInPost
 * @returns {Object} - Request body for POST /v2/ugcPosts
 */
export function buildPostBody({ personUrn, text, imageUrn, imageUrns, videoUrn, mentions }) {
  // Ensure personUrn is in full URN format
  const fullAuthorUrn = personUrn.startsWith('urn:li:person:')
    ? personUrn
    : `urn:li:person:${personUrn}`;

  // Backward compat: accept single imageUrn (string) or imageUrns (array)
  const allImageUrns = (imageUrns && imageUrns.length > 0)
    ? imageUrns
    : (imageUrn ? [imageUrn] : []);

  const attributes = buildMentionAttributes(mentions);

  const mediaElements = videoUrn
    ? [{
        status: 'READY',
        description: { text: 'Watch the demo' },
        media: videoUrn,
        title: { text: 'AI automation demo' },
      }]
    : allImageUrns.map((urn, i) => ({
        status: 'READY',
        description: {
          text: allImageUrns.length > 1 ? `Image ${i + 1} of ${allImageUrns.length}` : 'Blog post featured image',
        },
        media: urn,
        title: { text: 'Read the full article' },
      }));

  return {
    author: fullAuthorUrn,
    lifecycleState: 'PUBLISHED',
    specificContent: {
      'com.linkedin.ugc.ShareContent': {
        shareCommentary: {
          text: text,
          ...(attributes.length > 0 && { attributes }),
        },
        shareMediaCategory: videoUrn ? 'VIDEO' : (mediaElements.length > 0 ? 'IMAGE' : 'NONE'),
        ...(mediaElements.length > 0 && { media: mediaElements }),
      },
    },
    visibility: {
      'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC',
    },
  };
}

/**
 * Create LinkedIn post (UGC Post API)
 *
 * @param {Object} params - Post parameters
 * @param {string} params.personUrn - LinkedIn person URN
 * @param {string} params.text - Post text content (already cleaned of @[..](..) markers)
 * @param {string} [params.imageUrn] - Optional single image URN (backward compat)
 * @param {string[]} [params.imageUrns] - Optional array of image URNs (multi-image post)
 * @param {string} [params.videoUrn] - Optional video URN from uploadVideoToLinkedIn
 * @param {Array<{start: number, length: number, urn: string}>} [params.mentions] - Mentions from parseMentions
 * @returns {Promise<Object>} - Created post data
 */
export async function createLinkedInPost({ personUrn, text, imageUrn, imageUrns, videoUrn, mentions }) {
  const accessToken = process.env.LINKEDIN_ACCESS_TOKEN;

  try {
    console.log(`🤖 Creating LinkedIn post...`);

    const postBody = buildPostBody({ personUrn, text, imageUrn, imageUrns, videoUrn, mentions });

    const response = await fetch('https://api.linkedin.com/v2/ugcPosts', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0',
      },
      body: JSON.stringify(postBody),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`LinkedIn post creation failed (${response.status}): ${errorText}`);
    }

    const data = await response.json();
    console.log(`✅ Post created successfully: ${data.id}`);

    return data;

  } catch (error) {
    console.error('❌ Error creating LinkedIn post:', error.message);
    throw error;
  }
}

/**
 * Upload video to LinkedIn
 * LinkedIn video upload flow:
 *   1. Register upload (recipe: feedshare-video)
 *   2. Upload binary to provided URL
 *   3. Poll asset status until AVAILABLE (processing takes seconds to minutes)
 * Returns: Asset URN for use in post
 *
 * @param {string} videoPath - Local path to video file (.mov, .mp4, etc.)
 * @returns {Promise<string>} - LinkedIn asset URN
 */
export async function uploadVideoToLinkedIn(videoPath) {
  const accessToken = process.env.LINKEDIN_ACCESS_TOKEN;
  const personUrn = process.env.LINKEDIN_PERSON_URN;
  const fileSizeBytes = statSync(videoPath).size;

  const fullOwnerUrn = personUrn.startsWith('urn:li:person:')
    ? personUrn
    : `urn:li:person:${personUrn}`;

  try {
    console.log(`🎬 Step 1: Registering video upload (${(fileSizeBytes / 1024 / 1024).toFixed(1)} MB)...`);

    // Step 1: Register upload
    const registerResponse = await fetch('https://api.linkedin.com/v2/assets?action=registerUpload', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0',
      },
      body: JSON.stringify({
        registerUploadRequest: {
          recipes: ['urn:li:digitalmediaRecipe:feedshare-video'],
          owner: fullOwnerUrn,
          serviceRelationships: [{
            relationshipType: 'OWNER',
            identifier: 'urn:li:userGeneratedContent',
          }],
        },
      }),
    });

    if (!registerResponse.ok) {
      const errorText = await registerResponse.text();
      throw new Error(`Video registration failed (${registerResponse.status}): ${errorText}`);
    }

    const registerData = await registerResponse.json();
    const uploadUrl = registerData.value.uploadMechanism['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest'].uploadUrl;
    const asset = registerData.value.asset;

    console.log(`🎬 Step 2: Uploading video binary...`);

    // Step 2: Upload video binary
    const videoBuffer = readFileSync(videoPath);

    const uploadResponse = await fetch(uploadUrl, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/octet-stream',
        'Content-Length': String(fileSizeBytes),
      },
      body: videoBuffer,
    });

    if (!uploadResponse.ok) {
      const errorText = await uploadResponse.text();
      throw new Error(`Video upload failed (${uploadResponse.status}): ${errorText}`);
    }

    console.log(`🎬 Step 3: Waiting for LinkedIn to process video...`);

    // Step 3: Poll for processing completion
    // Extract asset ID from URN (e.g., "urn:li:digitalmediaAsset:D4E10AQHP..." -> full URN)
    const assetId = asset.replace('urn:li:digitalmediaAsset:', '');
    const maxPolls = 30; // 5 min max (30 * 10s)
    const pollInterval = 10_000; // 10 seconds

    for (let i = 0; i < maxPolls; i++) {
      await new Promise(resolve => setTimeout(resolve, pollInterval));

      const statusResponse = await fetch(`https://api.linkedin.com/v2/assets/${assetId}`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'X-Restli-Protocol-Version': '2.0.0',
        },
      });

      if (!statusResponse.ok) {
        console.log(`   ⏳ Poll ${i + 1}/${maxPolls}: status check returned ${statusResponse.status}, retrying...`);
        continue;
      }

      const statusData = await statusResponse.json();
      const recipes = statusData.recipes || [];
      const status = recipes[0]?.status || statusData.status || 'UNKNOWN';

      console.log(`   ⏳ Poll ${i + 1}/${maxPolls}: ${status}`);

      if (status === 'AVAILABLE') {
        console.log(`✅ Video processed successfully: ${asset}`);
        return asset;
      }

      if (status === 'FAILED' || status === 'CANCELED') {
        throw new Error(`Video processing ${status}. LinkedIn rejected the video.`);
      }
    }

    throw new Error(`Video processing timed out after ${maxPolls * pollInterval / 1000}s. Try a smaller file.`);

  } catch (error) {
    console.error('❌ Error uploading video to LinkedIn:', error.message);
    throw error;
  }
}

/**
 * Retry logic with exponential backoff
 * Useful for handling rate limits and transient errors
 *
 * @param {Function} fn - Async function to retry
 * @param {number} maxRetries - Maximum number of retry attempts (default: 3)
 * @returns {Promise<any>} - Result from function
 */
export async function retryWithBackoff(fn, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === maxRetries - 1) {
        throw error;
      }

      const delay = Math.pow(2, i) * 1000; // 1s, 2s, 4s
      console.log(`⚠️  Retry ${i + 1}/${maxRetries} after ${delay}ms... (${error.message})`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}
