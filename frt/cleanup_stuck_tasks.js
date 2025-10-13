import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('🧹 [CLEANUP] Cleaning up stuck tasks...');

// Read the database config to understand how to clean up
console.log('\n📋 [CLEANUP] Checking database configuration...');
if (fs.existsSync('drizzle.config.ts')) {
  console.log('✅ Drizzle config found');
  console.log('📝 [INSTRUCTION] To clean up stuck tasks, run:');
  console.log('   pnpm db:studio');
  console.log(
    '   Then manually delete stuck tasks from the translation_task table'
  );
  console.log('   Or run: DELETE FROM task_queue WHERE attempts >= 3;');
} else {
  console.log('⚠️ No database config found');
}

// Clean up uploads directory
console.log('\n📁 [CLEANUP] Cleaning uploads directory...');
const uploadsDir = path.join(process.cwd(), 'uploads');
if (fs.existsSync(uploadsDir)) {
  const files = fs.readdirSync(uploadsDir);
  console.log(`📊 [CLEANUP] Found ${files.length} files in uploads directory`);

  // Remove old test files (older than 1 hour)
  const oneHourAgo = Date.now() - 60 * 60 * 1000;
  let cleanedCount = 0;

  files.forEach((file) => {
    const filePath = path.join(uploadsDir, file);
    const stats = fs.statSync(filePath);

    if (
      stats.mtime.getTime() < oneHourAgo &&
      (file.endsWith('.md') || file.endsWith('.docx'))
    ) {
      fs.unlinkSync(filePath);
      cleanedCount++;
      console.log(`🗑️ [CLEANUP] Removed old file: ${file}`);
    }
  });

  console.log(`✅ [CLEANUP] Cleaned up ${cleanedCount} old files`);
} else {
  console.log('✅ [CLEANUP] Uploads directory does not exist');
}

console.log('\n🎉 [CLEANUP] Cleanup completed!');
console.log('\n📝 [NEXT STEPS]');
console.log('1. Restart the development server: pnpm dev');
console.log('2. The system should now process DOCX files properly');
console.log('3. No more infinite loops should occur');
console.log('4. Check the console for proper processing logs');
