// Test script to check database access
import { db } from './src/lib/server/db/index.ts';
import { project, aivProgress } from './src/lib/server/db/schema.ts';
import { eq, and } from 'drizzle-orm';

async function testDbAccess() {
  try {
    console.log('Testing database access...');

    // Try to fetch a project
    const dbProject = await db
      .select()
      .from(project)
      .where(eq(project.id, '_gY_6OFTWzf5GdrmlqC4d'))
      .limit(1);

    console.log('Project:', dbProject);

    // Try to insert a progress record
    const progressId = 'test-progress-' + Date.now();
    await db.insert(aivProgress).values({
      id: progressId,
      projectId: '_gY_6OFTWzf5GdrmlqC4d',
      step: 'preparing',
      command: null,
      result: null,
      log: null
    });

    console.log('Successfully inserted progress record');

    // Try to update the progress record
    await db
      .update(aivProgress)
      .set({
        step: 'running',
        updatedAt: new Date()
      })
      .where(eq(aivProgress.id, progressId));

    console.log('Successfully updated progress record');

    // Clean up
    await db.delete(aivProgress).where(eq(aivProgress.id, progressId));

    console.log('Successfully cleaned up test record');

    process.exit(0);
  } catch (error) {
    console.error('Error:', error);
    process.exit(1);
  }
}

testDbAccess();
