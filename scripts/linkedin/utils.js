import { readFileSync, appendFileSync } from 'fs';

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
          owner: personUrn,
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
 * @returns {Promise<Object>} - Created post data
 */
export async function createLinkedInPost({ personUrn, text, imageUrn }) {
  const accessToken = process.env.LINKEDIN_ACCESS_TOKEN;

  try {
    console.log(`🤖 Creating LinkedIn post...`);

    const postBody = {
      author: personUrn,
      lifecycleState: 'PUBLISHED',
      specificContent: {
        'com.linkedin.ugc.ShareContent': {
          shareCommentary: {
            text: text,
          },
          shareMediaCategory: imageUrn ? 'IMAGE' : 'NONE',
          ...(imageUrn && {
            media: [{
              status: 'READY',
              description: {
                text: 'Blog post featured image',
              },
              media: imageUrn,
              title: {
                text: 'Read the full article',
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
