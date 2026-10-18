// substrate/checker/vitest.aa-seed.config.ts — copied into packages/loot-core for every
// harness vitest run (never shown to agents). Wraps the package's own config and appends
// the fast-check seed setup (seed.setup.ts -> src/mocks/aa-seed.setup.ts):
// setupFiles = ['./src/mocks/setup.ts', <seed>]. Vitest 5 has no --setupFiles flag.
// Everything else (globals, excludes, timeouts, resolve conditions, plugins) is the
// repo's config unchanged.
import { mergeConfig } from 'vitest/config';

import base from './vitest.config';

export default mergeConfig(base, {
  test: {
    setupFiles: ['./src/mocks/aa-seed.setup.ts'],
  },
});
