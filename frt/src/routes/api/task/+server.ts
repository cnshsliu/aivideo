import { json, error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import { translationTask, taskQueue } from '$lib/server/db/schema';
import { eq, and, desc } from 'drizzle-orm';
import { verifySession } from '$lib/server/auth';
import { nanoid } from 'nanoid';

export async function GET({ request, url, cookies }) {
  try {
    console.log('📋 [TASK API] GET request for user tasks');

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log('❌ [TASK API] Unauthorized access attempt');
      return error(401, { message: 'Unauthorized' });
    }

    const userId = session.userId;
    console.log('📋 [TASK API] Fetching tasks for user:', userId);

    // Get user's tasks from database, ordered by creation date (newest first)
    const tasks = await db
      .select()
      .from(translationTask)
      .where(eq(translationTask.userId, userId))
      .orderBy(desc(translationTask.createdAt));

    console.log('📊 [TASK API] Found', tasks.length, 'tasks for user:', userId);
    console.log(
      '📋 [TASK API] Task statuses:',
      tasks.map((t) => `${t.id}:${t.status}`)
    );

    return json(tasks);
  } catch (err) {
    console.error('❌ [TASK API] User tasks retrieval error:', err);
    return error(500, { message: 'Internal server error' });
  }
}

export async function POST({ request, cookies }) {
  try {
    console.log('➕ [TASK API] POST request to create new task');

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log('❌ [TASK API] Unauthorized task creation attempt');
      return error(401, { message: 'Unauthorized' });
    }

    const userId = session.userId;
    console.log('📋 [TASK API] Creating task for user:', userId);

    const data = await request.json();
    console.log('📋 [TASK API] Task data:', data);

    // Validate required fields
    const {
      sourceLanguage,
      targetLanguage,
      sourceType,
      sourceContent,
      sourceFilePath,
      priority = 'normal'
    } = data;

    if (
      !sourceLanguage ||
      !targetLanguage ||
      !sourceType ||
      (!sourceContent && !sourceFilePath)
    ) {
      console.log('❌ [TASK API] Missing required fields');
      return error(400, {
        message:
          'Missing required fields: sourceLanguage, targetLanguage, sourceType, and either sourceContent or sourceFilePath'
      });
    }

    // Generate task IDs
    const taskId = nanoid();
    const internalId = nanoid();

    // Create task in database
    const newTask = {
      id: internalId,
      taskId: taskId,
      userId,
      sourceLanguage,
      targetLanguage,
      sourceType,
      sourceContent: sourceContent || null,
      sourceFilePath: sourceFilePath || null,
      status: 'pending',
      createdAt: new Date(),
      startedAt: null,
      completedAt: null,
      cost: '0.00',
      errorMessage: null,
      markdownPath: null,
      docxPath: null,
      pdfPath: null,
      pptxPath: null
    };

    await db.insert(translationTask).values(newTask);
    console.log('✅ [TASK API] Task created in database:', taskId);

    // Create task queue entry for continuous processing (no batch needed!)
    const queueId = nanoid();
    const priorityValue = priority === 'high' ? 10 : priority === 'low' ? 1 : 5;
    await db.insert(taskQueue).values({
      id: queueId,
      taskId: taskId,
      queueStatus: 'queued',
      priority: priorityValue,
      scheduledAt: new Date(),
      maxAttempts: 3
    });
    console.log(
      '✅ [TASK API] Task queued for continuous processing with priority:',
      priorityValue
    );

    // Return the created task
    return json(
      {
        id: taskId,
        taskId: taskId,
        userId: newTask.userId,
        status: newTask.status,
        sourceLanguage: newTask.sourceLanguage,
        targetLanguage: newTask.targetLanguage,
        sourceType: newTask.sourceType,
        sourceContent: newTask.sourceContent,
        sourceFilePath: newTask.sourceFilePath,
        createdAt: newTask.createdAt.toISOString(),
        startedAt: newTask.startedAt,
        completedAt: newTask.completedAt,
        cost: newTask.cost,
        errorMessage: newTask.errorMessage,
        markdownPath: newTask.markdownPath,
        docxPath: newTask.docxPath
      },
      { status: 201 }
    );
  } catch (err) {
    console.error('❌ [TASK API] Task creation error:', err);
    return error(500, { message: 'Internal server error' });
  }
}
