import { error } from '@sveltejs/kit';
import { verifySession } from '$lib/server/auth';
import { db } from '$lib/server/db';
import { project } from '$lib/server/db/schema';
import { eq } from 'drizzle-orm';
import fs from 'fs/promises';

export async function GET({ params, cookies }) {
  try {
    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log('❌ [LOG API] Unauthorized access attempt');
      return error(401, { message: 'Unauthorized' });
    }

    const { projectId } = params;

    // Fetch progress record
    const progressRecord = await db
      .select()
      .from(project)
      .where(eq(project.id, projectId))
      .limit(1);

    if (!progressRecord || progressRecord.length === 0) {
      return error(404, { message: 'Progress record not found' });
    }

    const record = progressRecord[0];

    // Check if log file exists
    if (!record.progressLog) {
      return error(404, { message: 'Log file not found' });
    }

    try {
      // Read log file content
      const logContent = await fs.readFile(record.progressLog, 'utf-8');
      return new Response(logContent, {
        headers: {
          'Content-Type': 'text/plain'
        }
      });
    } catch (fileErr: any) {
      // If file doesn't exist yet, return empty content (this is normal during early stages)
      if (fileErr.code === 'ENOENT') {
        console.log(
          "📖 [LOG API] Log file doesn't exist yet, returning empty content"
        );
        return new Response('', {
          headers: {
            'Content-Type': 'text/plain'
          }
        });
      }
      console.error('❌ [LOG API] Error reading log file:', fileErr);
      return error(500, { message: 'Error reading log file' });
    }
  } catch (err) {
    console.error('❌ [LOG API] Error:', err);
    return error(500, { message: 'Internal server error' });
  }
}
