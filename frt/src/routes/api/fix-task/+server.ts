import { json, error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { translationTask } from '$lib/server/db/schema';
import { eq } from 'drizzle-orm';
import { TranslationService } from '$lib/server/translation';

export async function POST({ request }) {
  try {
    const { taskId } = await request.json();

    if (!taskId) {
      return error(400, { message: 'Task ID is required' });
    }

    console.log('🔧 [FIX API] Fixing task:', taskId);

    // Get the current task
    const tasks = await db
      .select()
      .from(translationTask)
      .where(eq(translationTask.taskId, taskId))
      .limit(1);

    const task = tasks[0];
    if (!task) {
      return error(404, { message: 'Task not found' });
    }

    console.log('📋 [FIX API] Current task:', {
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
    console.log('🤖 [FIX API] Translating content...');
    console.log('📋 [FIX API] Translation request:', {
      sourceLanguage: task.sourceLanguage,
      targetLanguage: task.targetLanguage,
      contentLength: task.sourceContent?.length || 0
    });
    const result = await translationService.translate({
      content: task.sourceContent || '',
      sourceLanguage: task.sourceLanguage,
      targetLanguage: task.targetLanguage
    });

    console.log('✅ [FIX API] Translation result:', {
      originalLength: task.sourceContent?.length || 0,
      translatedLength: result.translatedContent.length,
      confidence: result.confidence,
      hasAlternatives: !!result.alternatives,
      alternativesCount: result.alternatives?.length || 0
    });

    // Update the task with the translation
    await db
      .update(translationTask)
      .set({
        sourceContent: result.translatedContent, // Store the translation
        completedAt: new Date()
      })
      .where(eq(translationTask.taskId, taskId));

    console.log('✅ [FIX API] Task fixed successfully!');

    return json({
      success: true,
      message: 'Task fixed successfully',
      translation: result.translatedContent
    });
  } catch (err) {
    console.error('❌ [FIX API] Task fix error:', err);
    return error(500, { message: 'Internal server error' });
  }
}
