// substrate/checker/vitest.aa.config.ts — copied into packages/loot-core at
// evaluation / baseline time only (never shown to agents), next to
// vitest.aa-seed.config.ts, which it extends.
//
// Vitest 5 has no `--setupFiles` CLI flag, so the probe is added by wrapping the
// seeded wrapper of the package's own config: mergeConfig concatenates arrays, giving
// setupFiles = ['./src/mocks/setup.ts', <fast-check seed>, <probe>]. Everything else
// (globals, excludes, resolve conditions, plugins) is the repo's config unchanged.
import { mergeConfig } from 'vitest/config';

import seeded from './vitest.aa-seed.config';

export default mergeConfig(seeded, {
  test: {
    setupFiles: [process.env.AA_PROBE_SETUP ?? './src/mocks/aa-probe.setup.ts'],
  },
});
