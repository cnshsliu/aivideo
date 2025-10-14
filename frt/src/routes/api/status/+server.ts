import { json, type RequestHandler } from '@sveltejs/kit';
import { verifySession } from '$lib/server/auth';
import { db } from '$lib/server/db';
import { translationTask } from '$lib/server/db/schema';
import { eq, or } from 'drizzle-orm';

export const GET: RequestHandler = async ({ url, cookies }) => {
  try {
    console.log('📊 [STATUS API] Received status request');

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log('❌ [STATUS API] Unauthorized - invalid session');
      return json({ error: 'Unauthorized' }, { status: 401 });
    }

    const taskId = url.searchParams.get('taskId');
    const batchId = url.searchParams.get('batchId');

    console.log('🔍 [STATUS API] Query params:', { taskId, batchId });

    if (!taskId && !batchId) {
      console.log('❌ [STATUS API] Missing taskId or batchId');
      return json({ error: 'taskId or batchId is required' }, { status: 400 });
    }

    if (batchId) {
      // Batch functionality removed - not supported in current system
      console.log('❌ [STATUS API] Batch functionality not supported');
      return json({ error: 'Batch functionality not supported' }, { status: 400 });
    }

    if (taskId) {
      // Get individual task status
      const [task] = await db
        .select()
        .from(translationTask)
        .where(
          or(eq(translationTask.taskId, taskId), eq(translationTask.id, taskId))
        );

      if (!task) {
        console.log('❌ [STATUS API] Task not found:', taskId);
        return json({ error: 'Task not found' }, { status: 404 });
      }

      console.log('✅ [STATUS API] Task status retrieved');
      return json({
        success: true,
        type: 'task',
        data: {
          task: {
            id: task.id,
            taskId: task.taskId,
            status: task.status,
            sourceLanguage: task.sourceLanguage,
            targetLanguage: task.targetLanguage,
            sourceType: task.sourceType,
            createdAt: task.createdAt,
            startedAt: task.startedAt,
            completedAt: task.completedAt,
            errorMessage: task.errorMessage,
            // batchId: task.batchId // Removed - field doesn't exist in schema
          },
          batch: null // No batch information in the new system
        }
      });
    }

    // This should never be reached, but TypeScript needs it
    return json({ error: 'Invalid request' }, { status: 400 });
  } catch (error) {
    console.error('❌ [STATUS API] Error checking status:', error);
    return json(
      {
        error: 'Failed to get status',
        details: error instanceof Error ? error.message : String(error)
      },
      { status: 500 }
    );
  }
};
