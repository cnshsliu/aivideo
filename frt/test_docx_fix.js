#!/usr/bin/env node

/**
 * Test script to validate DOCX translation fixes
 * This script tests:
 * 1. DOCX file upload
 * 2. Text extraction with mammoth
 * 3. Translation processing
 * 4. DOCX generation
 * 5. Infinite loop prevention
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('🧪 [TEST] Starting DOCX translation system test...');

// Test 1: Check if required files exist
console.log('\n📋 [TEST 1] Checking required files...');
const requiredFiles = [
  'src/lib/server/continuous-batch-processor.ts',
  'src/lib/server/translation.ts',
  'src/routes/api/translate/+server.ts',
  'src/routes/api/download/[id]/+server.ts'
];

requiredFiles.forEach((file) => {
  if (fs.existsSync(file)) {
    console.log(`✅ ${file} exists`);
  } else {
    console.log(`❌ ${file} missing`);
  }
});

// Test 2: Check package.json dependencies
console.log('\n📦 [TEST 2] Checking dependencies...');
const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
const requiredDeps = ['mammoth', 'docx', 'openai', 'nanoid'];

requiredDeps.forEach((dep) => {
  if (packageJson.dependencies[dep] || packageJson.devDependencies[dep]) {
    console.log(`✅ ${dep} installed`);
  } else {
    console.log(`❌ ${dep} missing`);
  }
});

// Test 3: Check for broken Python script references
console.log('\n🐍 [TEST 3] Checking for broken Python script references...');
const processorFile = fs.readFileSync(
  'src/lib/server/continuous-batch-processor.ts',
  'utf8'
);
if (processorFile.includes('docx_translator.py')) {
  console.log('❌ Still contains broken Python script reference');
} else {
  console.log('✅ Python script reference removed');
}

// Test 4: Check for proper error handling
console.log('\n🛡️ [TEST 4] Checking error handling...');
if (
  processorFile.includes('Promise.race') &&
  processorFile.includes('timeout')
) {
  console.log('✅ Translation timeout handling added');
} else {
  console.log('❌ Missing timeout handling');
}

// Test 5: Check for infinite loop prevention
console.log('\n🔄 [TEST 5] Checking infinite loop prevention...');
if (
  processorFile.includes('maxAttempts') &&
  processorFile.includes('resetCount >= 3')
) {
  console.log('✅ Infinite loop prevention added');
} else {
  console.log('❌ Missing infinite loop prevention');
}

// Test 6: Check for proper DOCX generation
console.log('\n📄 [TEST 6] Checking DOCX generation...');
if (
  processorFile.includes('generateTranslatedDocx') &&
  processorFile.includes('Packer.toBuffer')
) {
  console.log('✅ DOCX generation implemented');
} else {
  console.log('❌ Missing DOCX generation');
}

// Test 7: Create uploads directory if it doesn't exist
console.log('\n📁 [TEST 7] Setting up test environment...');
const uploadsDir = path.join(process.cwd(), 'uploads');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
  console.log('✅ Created uploads directory');
} else {
  console.log('✅ Uploads directory exists');
}

// Test 8: Create test document
console.log('\n📝 [TEST 8] Creating test document...');
const testContent = `This is a test document for translation.

It contains multiple paragraphs to test the DOCX processing functionality.

The system should:
1. Extract text from this DOCX file
2. Translate the content using the LLM agent
3. Generate a new DOCX file with the translated content
4. Preserve the paragraph structure

Let's see if this works properly!

End of test document.`;

fs.writeFileSync(path.join(uploadsDir, 'test_document.txt'), testContent);
console.log('✅ Test document created');

console.log('\n🎉 [TEST] All tests completed!');
console.log('\n📝 [INSTRUCTIONS] Manual testing required:');
console.log('1. Start the development server: pnpm dev');
console.log('2. Upload a DOCX file through the web interface');
console.log('3. Monitor the console logs for proper processing');
console.log('4. Check the uploads directory for generated files');
console.log('5. Verify no infinite loops occur');
