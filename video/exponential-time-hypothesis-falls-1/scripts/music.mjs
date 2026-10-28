// Writes the music bed (public/music/bed.wav) with scripts/music_local.py.
// Uses python3 when it has numpy, else `uv run --with numpy` (cached after the first run).
// Usage: npm run music [-- seconds]
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { at } from './lib.mjs';

export function makeMusicBed(seconds = 80) {
  const script = at('scripts', 'music_local.py');
  const hasNumpy = spawnSync('python3', ['-c', 'import numpy'], { stdio: 'ignore' }).status === 0;
  const [cmd, args] = hasNumpy ? ['python3', [script]] : ['uv', ['run', '--quiet', '--with', 'numpy', 'python', script]];
  const r = spawnSync(cmd, [...args, String(seconds)], { stdio: 'inherit', cwd: at() });
  if (r.status !== 0) throw new Error('music bed failed: needs python3 with numpy, or uv (brew install uv)');
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) makeMusicBed(+(process.argv[2] ?? 80));
