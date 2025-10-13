import { json, error, type RequestHandler } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { translationTask, taskQueue } from '$lib/server/db/schema';
import { eq, and, desc } from 'drizzle-orm';
import { verifySession } from '$lib/server/auth';
import { nanoid } from 'nanoid';

export async function GET({ params }) {
  try {
    const { id } = params;
    console.log('🔍 [TASK API] GET request for task ID:', id);

    // Query database for the task - search by taskId (foreign key) instead of id
    const tasks = await db
      .select()
      .from(translationTask)
      .where(eq(translationTask.taskId, id))
      .limit(1);

    const task = tasks[0] || null;
    console.log('📋 [TASK API] Task found:', task ? 'YES' : 'NO');

    if (!task) {
      console.log('❌ [TASK API] Task not found:', id);
      return error(404, { message: 'Task not found' });
    }

    console.log(
      '✅ [TASK API] Task retrieved successfully:',
      task.id,
      'Status:',
      task.status
    );
    return json(task);
  } catch (err) {
    console.error('❌ [TASK API] Task retrieval error:', err);
    return error(500, { message: 'Internal server error' });
  }
}

export async function DELETE({ params }) {
  try {
    const { id } = params;
    console.log('🗑️ [TASK API] DELETE request for task ID:', id);

    // Get task details first from database - search by taskId (foreign key)
    const tasks = await db
      .select()
      .from(translationTask)
      .where(eq(translationTask.taskId, id))
      .limit(1);

    const task = tasks[0] || null;

    if (!task) {
      console.log('❌ [TASK API] Task not found for deletion:', id);
      return error(404, { message: 'Task not found' });
    }

    console.log(
      '📋 [TASK API] Deleting task:',
      task.id,
      'Status:',
      task.status
    );

    // Delete files from disk if they exist
    const { unlink } = await import('fs/promises');
    if (task.sourceFilePath) {
      try {
        await unlink(task.sourceFilePath);
        console.log('🗑️ [TASK API] Deleted source file:', task.sourceFilePath);
      } catch (err) {
        console.warn('⚠️ [TASK API] Failed to delete source file:', err);
      }
    }
    if (task.markdownPath) {
      try {
        await unlink(task.markdownPath);
        console.log('🗑️ [TASK API] Deleted markdown file:', task.markdownPath);
      } catch (err) {
        console.warn('⚠️ [TASK API] Failed to delete markdown file:', err);
      }
    }

    // Delete from database - use the correct field (taskId, not id)
    await db.delete(translationTask).where(eq(translationTask.taskId, id));

    // Also remove from task queue if it exists
    await db.delete(taskQueue).where(eq(taskQueue.taskId, id));

    console.log('✅ [TASK API] Task deleted from database');

    return json({
      success: true,
      message: 'Task deleted successfully'
    });
  } catch (err) {
    console.error('❌ [TASK API] Task deletion error:', err);
    return error(500, { message: 'Internal server error' });
  }
}
