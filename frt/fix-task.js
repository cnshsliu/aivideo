// Fix existing task by updating it with proper translation
import { db } from './src/lib/server/db/index.js';
import { translationTask } from './src/lib/server/db/schema.js';
import { eq } from 'drizzle-orm';
import { TranslationService } from './src/lib/server/translation.js';

async function fixTask() {
  const taskId = 'kzH6zVH5wRxLw7-1KouCJ';

  try {
    console.log('🔧 Fixing task:', taskId);

    // Get the current task
    const tasks = await db
      .select()
      .from(translationTask)
      .where(eq(translationTask.taskId, taskId))
      .limit(1);

    const task = tasks[0];
    if (!task) {
      console.log('❌ Task not found');
      return;
    }

    console.log('📋 Current task:', {
      id: task.id,
      taskId: task.taskId,
      status: task.status,
      sourceLanguage: task.sourceLanguage,
      targetLanguage: task.targetLanguage,
      sourceContent: task.sourceContent?.substring(0, 50) + '...'
    });

    // Initialize translation service
    const translationService = new TranslationService();

    // Translate the content
    console.log('🤖 Translating content...');
    const result = await translationService.translate({
      content: task.sourceContent || '',
      sourceLanguage: task.sourceLanguage,
      targetLanguage: task.targetLanguage
    });

    console.log('✅ Translation result:', {
      originalLength: task.sourceContent?.length || 0,
      translatedLength: result.translatedContent.length,
      confidence: result.confidence
    });

    // Update the task with the translation
    await db
      .update(translationTask)
      .set({
        sourceContent: result.translatedContent, // Store the translation
        completedAt: new Date()
      })
      .where(eq(translationTask.taskId, taskId));

    console.log('✅ Task fixed successfully!');
  } catch (error) {
    console.error('❌ Failed to fix task:', error);
  }
}

fixTask().catch(console.error);
