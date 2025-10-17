import { json, error } from '@sveltejs/kit';
import { verifySession } from '$lib/server/auth';
import { db } from '$lib/server/db';
import { project } from '$lib/server/db/schema';
import { eq } from 'drizzle-orm';
import { LLMManager } from '$lib/server/llm';

export async function POST({ params, request, cookies }) {
  try {
    console.log(
      '🎬 [STATIC SUBTITLES API] POST request to generate static subtitles for project:',
      params.projectId
    );

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log('❌ [STATIC SUBTITLES API] Unauthorized access attempt');
      return error(401, { message: 'Unauthorized' });
    }

    const { projectId } = params;
    const body = await request.json();
    const { folder } = body;

    // Fetch project
    const dbProject = await db
      .select()
      .from(project)
      .where(eq(project.id, projectId))
      .limit(1);

    if (!dbProject || dbProject.length === 0) {
      return error(404, { message: 'Project not found' });
    }

    const selectedProject = dbProject[0];

    // Get LLM provider from environment
    const llmProvider = process.env.LLM_PROVIDER || 'qwen';
    console.log(`🤖 [STATIC SUBTITLES API] Using LLM provider: ${llmProvider}`);

    // Generate subtitles directly using TypeScript LLM module
    const llmManager = new LLMManager();
    const subtitles = await llmManager.generateSubtitles(
      selectedProject.news || undefined,
      selectedProject.prompt || undefined,
      selectedProject.commonPrompt || undefined,
      llmProvider
    );

    // Join subtitles with newlines for storage
    const processedResult = subtitles.join('\n');

    // Update the project with the generated subtitles
    if (processedResult && processedResult.trim()) {
      await db
        .update(project)
        .set({
          staticSubtitle: processedResult.trim(),
          updatedAt: new Date()
        })
        .where(eq(project.id, projectId));
    }

    console.log(
      '✅ [STATIC SUBTITLES API] Static subtitles generated:',
      projectId
    );

    return json({ success: true, result: processedResult });
  } catch (err) {
    console.error(
      '❌ [STATIC SUBTITLES API] Static subtitles generation error:',
      err
    );
    return error(500, { message: 'Internal server error' });
  }
}
