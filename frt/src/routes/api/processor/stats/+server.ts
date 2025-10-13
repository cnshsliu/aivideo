import { json, type RequestHandler } from '@sveltejs/kit';
import { continuousBatchProcessor } from '$lib/server/continuous-batch-processor.js';

export const GET: RequestHandler = async () => {
  try {
    console.log('📊 [PROCESSOR STATS] Request for processing statistics');

    const stats = await continuousBatchProcessor.getStatistics();

    console.log('✅ [PROCESSOR STATS] Retrieved statistics:', stats);

    return json({
      success: true,
      stats,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('❌ [PROCESSOR STATS] Error retrieving statistics:', error);
    return json(
      {
        error: 'Failed to retrieve processing statistics',
        details: error instanceof Error ? error.message : String(error)
      },
      { status: 500 }
    );
  }
};
