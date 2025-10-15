import { json, error } from '@sveltejs/kit';
import { verifySession } from '$lib/server/auth';
import { db } from '$lib/server/db';
import { project } from '$lib/server/db/schema';
import { eq, and } from 'drizzle-orm';
import path from 'path';

export async function GET({ params, cookies }) {
  try {
    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log('❌ [PROJECT GET API] Unauthorized access attempt');
      return error(401, { message: 'Unauthorized' });
    }

    const { projectId } = params;

    // Fetch project
    const dbProject = await db
      .select()
      .from(project)
      .where(and(eq(project.id, projectId), eq(project.userId, session.userId)))
      .limit(1);

    if (!dbProject || dbProject.length === 0) {
      return error(404, { message: 'Project not found' });
    }

    return json(dbProject[0]);
  } catch (err) {
    console.error('❌ [PROJECT GET API] Project fetch error:', err);
    return error(500, { message: 'Internal server error' });
  }
}

export async function PUT({ params, request, cookies }) {
  try {
    console.log(
      '📝 [PROJECT UPDATE API] PUT request to update project:',
      params.projectId
    );

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log('❌ [PROJECT UPDATE API] Unauthorized access attempt');
      return error(401, { message: 'Unauthorized' });
    }

    const { projectId } = params;
    const {
      title,
      video_title,
      name,
      prompt,
      staticSubtitle,
      desc,
      brief,
      bodytext,
      bodytextLength,
      keepTitle,
      addTimestampToTitle,
      titleFont,
      titleFontSize,
      titlePosition,
      sortOrder,
      keepClipLength,
      clipNum,
      subtitleFont,
      subtitleFontSize,
      subtitlePosition,
      genSubtitle,
      genVoice,
      llmProvider,
      bgmFile,
      bgmFadeIn,
      bgmFadeOut,
      bgmVolume
    } = await request.json();

    if (!title || !name) {
      return error(400, { message: 'Title and name are required' });
    }

    // Check if project exists and belongs to user
    const dbProject = await db
      .select()
      .from(project)
      .where(and(eq(project.id, projectId), eq(project.userId, session.userId)))
      .limit(1);

    if (!dbProject || dbProject.length === 0) {
      return error(404, { message: 'Project not found' });
    }

    // Check uniqueness of name
    const existingName = await db
      .select()
      .from(project)
      .where(and(eq(project.name, name), eq(project.userId, session.userId)))
      .limit(1);

    if (
      existingName &&
      existingName.length > 0 &&
      existingName[0].id !== projectId
    ) {
      return json({ message: 'Project name already exists' }, { status: 409 });
    }

    // Check uniqueness of title
    const existingTitle = await db
      .select()
      .from(project)
      .where(and(eq(project.title, title), eq(project.userId, session.userId)))
      .limit(1);

    if (
      existingTitle &&
      existingTitle.length > 0 &&
      existingTitle[0].id !== projectId
    ) {
      return json({ message: 'Project title already exists' }, { status: 409 });
    }

    // Update project
    console.log('prompt=', prompt);
    console.log('staticSubtitle=', staticSubtitle);
    console.log('desc=', desc);
    console.log('brief=', brief);
    console.log('video_title=', video_title);
    console.log('keepTitle=', keepTitle);
    console.log('addTimestampToTitle=', addTimestampToTitle);
    console.log('titleFont=', titleFont);
    console.log('titleFontSize=', titleFontSize);
    console.log('titlePosition=', titlePosition);
    console.log('sortOrder=', sortOrder);
    console.log('keepClipLength=', keepClipLength);
    console.log('clipNum=', clipNum);
    console.log('subtitleFont=', subtitleFont);
    console.log('subtitleFontSize=', subtitleFontSize);
    console.log('subtitlePosition=', subtitlePosition);
    console.log('genSubtitle=', genSubtitle);
    console.log('genVoice=', genVoice);
    console.log('llmProvider=', llmProvider);

    await db
      .update(project)
      .set({
        title,
        video_title,
        name,
        prompt,
        staticSubtitle,
        desc,
        brief,
        bodytext,
        bodytextLength,
        keepTitle,
        addTimestampToTitle,
        titleFont,
        titleFontSize,
        titlePosition,
        sortOrder,
        keepClipLength,
        clipNum,
        subtitleFont,
        subtitleFontSize,
        subtitlePosition,
        genSubtitle,
        genVoice,
        llmProvider,
        bgmFile,
        bgmFadeIn,
        bgmFadeOut,
        bgmVolume,
        updatedAt: new Date()
      })
      .where(
        and(eq(project.id, projectId), eq(project.userId, session.userId))
      );

    console.log(
      '✅ [PROJECT UPDATE API] Project updated:',
      projectId,
      'name=',
      name,
      'title=',
      title
    );

    return json({ success: true });
  } catch (err) {
    console.error('❌ [PROJECT UPDATE API] Project update error:', err);
    return error(500, { message: 'Internal server error' });
  }
}

// DELETE method to delete a project
export async function DELETE({ params, cookies }) {
  try {
    console.log(
      '🗑️ [PROJECT DELETE API] DELETE request for project:',
      params.projectId
    );

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log('❌ [PROJECT DELETE API] Unauthorized access attempt');
      return error(401, { message: 'Unauthorized' });
    }

    const { projectId } = params;

    // Check if project exists and belongs to user
    const dbProject = await db
      .select()
      .from(project)
      .where(and(eq(project.id, projectId), eq(project.userId, session.userId)))
      .limit(1);

    if (!dbProject || dbProject.length === 0) {
      return error(404, { message: 'Project not found' });
    }

    const projectName = dbProject[0].name;

    // Delete project from database
    await db
      .delete(project)
      .where(
        and(eq(project.id, projectId), eq(project.userId, session.userId))
      );

    // Delete project folder from vault
    try {
      const { rm } = await import('fs/promises');
      const vaultPath = process.env.AIV_VAULT_FOLDER || './vault';
      const userPath = path.join(vaultPath, session.username);
      const projectPath = path.join(userPath, projectName);

      await rm(projectPath, { recursive: true, force: true });
      console.log(
        '🗑️ [PROJECT DELETE API] Project folder deleted:',
        projectPath
      );
    } catch (fsErr) {
      console.warn(
        '⚠️ [PROJECT DELETE API] Failed to delete project folder:',
        fsErr
      );
    }

    console.log('✅ [PROJECT DELETE API] Project deleted:', projectId);

    return json({ success: true });
  } catch (err) {
    console.error('❌ [PROJECT DELETE API] Project deletion error:', err);
    return error(500, { message: 'Internal server error' });
  }
}
