import { execSync } from 'child_process';

/**
 * Suite de tests completa
 * Ejecuta todos los tests en orden
 */
async function runAllTests() {
  console.log('🧪 Running LinkedIn Automation Test Suite\n');
  console.log('═'.repeat(60));

  const tests = [
    {
      name: 'Post Detection & Parsing',
      command: 'node scripts/linkedin/test-detect-posts.js',
      required: true,
    },
    {
      name: 'Summary Preparation (Mock)',
      command: 'node scripts/linkedin/test-summary.js',
      required: true,
    },
    {
      name: 'Gemini API Integration',
      command: 'node scripts/linkedin/test-gemini.js',
      required: false,
      skipMessage: 'Skipped (requires GEMINI_API_KEY)',
    },
  ];

  let passed = 0;
  let failed = 0;
  let skipped = 0;

  for (const test of tests) {
    console.log(`\n\n🧪 Test: ${test.name}`);
    console.log('─'.repeat(60));

    try {
      // Check if test should be skipped
      if (!test.required && test.name.includes('Gemini') && !process.env.GEMINI_API_KEY) {
        console.log(`⏭️  ${test.skipMessage}`);
        skipped++;
        continue;
      }

      execSync(test.command, { stdio: 'inherit' });
      passed++;
    } catch (error) {
      console.error(`\n❌ Test failed: ${test.name}`);
      failed++;
      if (test.required) {
        console.error('\n⚠️  This is a required test. Stopping suite.');
        break;
      }
    }
  }

  console.log('\n\n═'.repeat(60));
  console.log('📊 Test Results:');
  console.log(`  ✅ Passed: ${passed}`);
  console.log(`  ❌ Failed: ${failed}`);
  console.log(`  ⏭️  Skipped: ${skipped}`);
  console.log(`  📝 Total: ${tests.length}`);

  if (failed === 0) {
    console.log('\n✅ All required tests passed!\n');
    console.log('Next steps:');
    console.log('  1. Get Gemini API key: https://aistudio.google.com/apikey');
    console.log('  2. Test Gemini: export GEMINI_API_KEY=xxx && npm run test:gemini');
    console.log('  3. Set up LinkedIn OAuth: node scripts/linkedin-oauth-setup.js');
    console.log('  4. Configure GitHub Secrets');
    console.log('  5. Push to main and watch it work!\n');
    process.exit(0);
  } else {
    console.log('\n❌ Some tests failed. Fix errors before proceeding.\n');
    process.exit(1);
  }
}

runAllTests();
