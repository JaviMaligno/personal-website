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
 * Create LinkedIn post (UGC Post API)
 *
 * @param {Object} params - Post parameters
 * @param {string} params.personUrn - LinkedIn person URN
 * @param {string} params.text - Post text content
 * @param {string} [params.imageUrn] - Optional image URN from uploadImageToLinkedIn
 * @param {string} [params.videoUrn] - Optional video URN from uploadVideoToLinkedIn
 * @returns {Promise<Object>} - Created post data
 */
export async function createLinkedInPost({ personUrn, text, imageUrn, videoUrn }) {
  const accessToken = process.env.LINKEDIN_ACCESS_TOKEN;

  try {
    console.log(`🤖 Creating LinkedIn post...`);

    // Ensure personUrn is in full URN format
    const fullAuthorUrn = personUrn.startsWith('urn:li:person:')
      ? personUrn
      : `urn:li:person:${personUrn}`;

    const postBody = {
      author: fullAuthorUrn,
      lifecycleState: 'PUBLISHED',
      specificContent: {
        'com.linkedin.ugc.ShareContent': {
          shareCommentary: {
            text: text,
          },
          shareMediaCategory: videoUrn ? 'VIDEO' : (imageUrn ? 'IMAGE' : 'NONE'),
          ...((videoUrn || imageUrn) && {
            media: [{
              status: 'READY',
              description: {
                text: videoUrn ? 'Watch the demo' : 'Blog post featured image',
              },
              media: videoUrn || imageUrn,
              title: {
                text: videoUrn ? 'AI automation demo' : 'Read the full article',
              },
            }],
          }),
        },
      },
      visibility: {
        'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC',
      },
    };

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
