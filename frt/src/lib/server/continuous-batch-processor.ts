import { db } from './db';
import { translationTask, taskQueue } from './db/schema';
import { eq, and, lt, desc } from 'drizzle-orm';
import { TranslationService } from './translation';

interface ProcessingStatistics {
  totalTasks: number;
  pendingTasks: number;
  processingTasks: number;
  completedTasks: number;
  failedTasks: number;
  averageProcessingTime: number;
}

class ContinuousBatchProcessor {
  private translationService: TranslationService;
  private isProcessing: boolean = false;
  private processingStats: ProcessingStatistics = {
    totalTasks: 0,
    pendingTasks: 0,
    processingTasks: 0,
    completedTasks: 0,
    failedTasks: 0,
    averageProcessingTime: 0
  };

  constructor() {
    this.translationService = new TranslationService();
  }

  async processNextBatch(): Promise<void> {
    if (this.isProcessing) {
      console.log('🔄 [BATCH PROCESSOR] Already processing, skipping...');
      return;
    }

    this.isProcessing = true;

    try {
      console.log('🔄 [BATCH PROCESSOR] Starting batch processing...');

      // Get pending tasks from queue
      const pendingTasks = await db
        .select()
        .from(taskQueue)
        .where(eq(taskQueue.queueStatus, 'queued'))
        .orderBy(desc(taskQueue.priority), taskQueue.scheduledAt)
        .limit(5); // Process up to 5 tasks at a time

      if (pendingTasks.length === 0) {
        console.log('🔄 [BATCH PROCESSOR] No pending tasks found');
        return;
      }

      console.log(`🔄 [BATCH PROCESSOR] Processing ${pendingTasks.length} tasks`);

      for (const queueItem of pendingTasks) {
        await this.processTask(queueItem);
      }

      console.log('✅ [BATCH PROCESSOR] Batch processing completed');
    } catch (error) {
      console.error('❌ [BATCH PROCESSOR] Batch processing error:', error);
    } finally {
      this.isProcessing = false;
    }
  }

  private async processTask(queueItem: any): Promise<void> {
    const startTime = Date.now();

    try {
      console.log(`🔄 [BATCH PROCESSOR] Processing task: ${queueItem.taskId}`);

      // Mark task as started
      await db
        .update(taskQueue)
        .set({
          queueStatus: 'processing',
          startedAt: new Date()
        })
        .where(eq(taskQueue.id, queueItem.id));

      // Get the actual task
      const [task] = await db
        .select()
        .from(translationTask)
        .where(eq(translationTask.taskId, queueItem.taskId))
        .limit(1);

      if (!task) {
        throw new Error(`Task ${queueItem.taskId} not found`);
      }

      // Update task status
      await db
        .update(translationTask)
        .set({
          status: 'processing',
          startedAt: new Date()
        })
        .where(eq(translationTask.taskId, queueItem.taskId));

      // Perform translation
      const result = await this.translationService.translate({
        content: task.sourceContent || '',
        sourceLanguage: task.sourceLanguage,
        targetLanguage: task.targetLanguage
      });

      // Update task with results
      await db
        .update(translationTask)
        .set({
          status: 'completed',
          sourceContent: result.translatedContent, // Store translated content
          completedAt: new Date()
        })
        .where(eq(translationTask.taskId, queueItem.taskId));

      // Mark queue item as completed
      await db
        .update(taskQueue)
        .set({
          queueStatus: 'completed',
          completedAt: new Date()
        })
        .where(eq(taskQueue.id, queueItem.id));

      const processingTime = Date.now() - startTime;
      console.log(`✅ [BATCH PROCESSOR] Task ${queueItem.taskId} completed in ${processingTime}ms`);

    } catch (error) {
      const processingTime = Date.now() - startTime;
      console.error(`❌ [BATCH PROCESSOR] Task ${queueItem.taskId} failed after ${processingTime}ms:`, error);

      // Mark task as failed
      await db
        .update(translationTask)
        .set({
          status: 'failed',
          errorMessage: error instanceof Error ? error.message : 'Unknown error'
        })
        .where(eq(translationTask.taskId, queueItem.taskId));

      // Update queue item
      await db
        .update(taskQueue)
        .set({
          queueStatus: 'failed',
          errorMessage: error instanceof Error ? error.message : 'Unknown error',
          completedAt: new Date()
        })
        .where(eq(taskQueue.id, queueItem.id));
    }
  }

  async getStatistics(): Promise<ProcessingStatistics> {
    try {
      // Get counts from database
      const [stats] = await db
        .select({
          totalTasks: db.$count(translationTask),
          pendingTasks: db.$count(translationTask, eq(translationTask.status, 'pending')),
          processingTasks: db.$count(translationTask, eq(translationTask.status, 'processing')),
          completedTasks: db.$count(translationTask, eq(translationTask.status, 'completed')),
          failedTasks: db.$count(translationTask, eq(translationTask.status, 'failed'))
        })
        .from(translationTask);

      // Calculate average processing time (simplified)
      const completedTasks = await db
        .select()
        .from(translationTask)
        .where(and(
          eq(translationTask.status, 'completed'),
          lt(translationTask.startedAt, translationTask.completedAt)
        ));

      let totalProcessingTime = 0;
      let processedCount = 0;

      for (const task of completedTasks) {
        if (task.startedAt && task.completedAt) {
          totalProcessingTime += task.completedAt.getTime() - task.startedAt.getTime();
          processedCount++;
        }
      }

      const averageProcessingTime = processedCount > 0 ? totalProcessingTime / processedCount : 0;

      this.processingStats = {
        totalTasks: stats.totalTasks || 0,
        pendingTasks: stats.pendingTasks || 0,
        processingTasks: stats.processingTasks || 0,
        completedTasks: stats.completedTasks || 0,
        failedTasks: stats.failedTasks || 0,
        averageProcessingTime
      };

      return this.processingStats;
    } catch (error) {
      console.error('❌ [BATCH PROCESSOR] Error getting statistics:', error);
      return this.processingStats;
    }
  }
}

// Export singleton instance
export const continuousBatchProcessor = new ContinuousBatchProcessor();
