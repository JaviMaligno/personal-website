import { existsSync, readdirSync, statSync } from 'fs';
import { resolve, extname, basename } from 'path';

// Media discovery for post-standalone.js (in priority order):
//   0. Video in the folder named like the post (scripts/linkedin/posts/my-post/*.mp4),
//      so several scheduled video posts can coexist
//   1. Video at repo root: video-linkedin.* (single video, excludes images)
//   2. Images in the folder named like the post (natural sort)
//   3. Numbered images at repo root: image-1.png, image-2.jpg, ...
//   4. Single image at repo root: image.png/.jpg/... (legacy behavior)

const VIDEO_EXTENSIONS = ['.mov', '.mp4', '.avi', '.mkv', '.webm'];
const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif'];
const MAX_IMAGES = 20;

function findImages(basePath, postPath) {
  // Priority 1: folder with the same name as the post .txt
  // e.g. scripts/linkedin/posts/my-post.txt → scripts/linkedin/posts/my-post/
  const postDir = postPath.replace(/\.txt$/, '');
  if (existsSync(postDir) && statSync(postDir).isDirectory()) {
    const images = readdirSync(postDir)
      .filter(f => IMAGE_EXTENSIONS.includes(extname(f).toLowerCase()))
      .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
      .map(f => resolve(postDir, f));
    if (images.length > 0) return { images, source: `posts/${basename(postDir)}/` };
  }

  // Priority 2: numbered images at repo root (image-1.png, image-2.jpg, ...)
  const numbered = [];
  for (let i = 1; i <= MAX_IMAGES; i++) {
    for (const ext of IMAGE_EXTENSIONS) {
      const fullPath = resolve(basePath, `image-${i}${ext}`);
      if (existsSync(fullPath)) {
        numbered.push(fullPath);
        break; // only one extension per index
      }
    }
  }
  if (numbered.length > 0) return { images: numbered, source: 'repo root (image-N.*)' };

  // Priority 3: single image.png fallback (legacy)
  for (const ext of IMAGE_EXTENSIONS) {
    const fullPath = resolve(basePath, `image${ext}`);
    if (existsSync(fullPath)) return { images: [fullPath], source: 'repo root (image.*)' };
  }

  return { images: [], source: null };
}

export function findMedia(basePath, postPath) {
  const postDir = postPath.replace(/\.txt$/, '');
  if (existsSync(postDir) && statSync(postDir).isDirectory()) {
    const videos = readdirSync(postDir).filter(f => VIDEO_EXTENSIONS.includes(extname(f).toLowerCase())).sort();
    if (videos.length > 0) return { type: 'video', paths: [resolve(postDir, videos[0])], source: `posts/${basename(postDir)}/` };
  }

  // Video files matching video-linkedin.* pattern at repo root (video excludes images)
  for (const ext of VIDEO_EXTENSIONS) {
    const fullPath = resolve(basePath, `video-linkedin${ext}`);
    if (existsSync(fullPath)) return { type: 'video', paths: [fullPath], source: 'repo root' };
  }

  const { images, source } = findImages(basePath, postPath);
  if (images.length > 0) return { type: 'image', paths: images, source };

  return null;
}

