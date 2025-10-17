import { json, error } from '@sveltejs/kit';
import { verifySession } from '$lib/server/auth';
import { db } from '$lib/server/db';
import { project, material } from '$lib/server/db/schema';
import fs from 'fs/promises';
import path from 'path';
import { nanoid } from 'nanoid';
import { eq } from 'drizzle-orm';

export async function POST({ params, cookies, request }) {
  try {
    console.log(
      '📋 [PROJECT COPY API] POST request to copy project:',
      params.projectId
    );

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log('❌ [PROJECT COPY API] Unauthorized access attempt');
      return error(401, { message: 'Unauthorized' });
    }

    const { projectId } = params;
    const { name, title } = await request.json();

    // Get project from database first
    const dbProject = await db
      .select()
      .from(project)
      .where(eq(project.id, projectId))
      .limit(1);

    if (!dbProject || dbProject.length === 0) {
      return error(404, { message: 'Project not found' });
    }

    const projectName = dbProject[0].name;
    const vaultPath = process.env.AIV_VAULT_FOLDER || './vault';
    const userPath = path.join(vaultPath, session.username);
    const sourcePath = path.join(userPath, projectName);

    // Check if project directory exists
    try {
      await fs.access(sourcePath);
    } catch {
      return error(404, { message: 'Project directory not found' });
    }

    try {
      // Use provided name or generate new project name (copy)
      let newProjectName = name || `${projectName}-copy`;
      let counter = 1;
      let newProjectPath = path.join(userPath, newProjectName);

      // If name was provided, check if it already exists and add counter if needed
      if (name) {
        while (
          await fs
            .access(newProjectPath)
            .then(() => true)
            .catch(() => false)
        ) {
          newProjectName = `${name}-${counter}`;
          newProjectPath = path.join(userPath, newProjectName);
          counter++;
        }
      }

      // Copy project directory recursively
      await copyDirectoryRecursive(sourcePath, newProjectPath);

      // Generate new project ID
      const newProjectId = nanoid();

      // Create new project in database
      const newProject = await db
        .insert(project)
        .values({
          id: newProjectId,
          name: newProjectName,
          title: title || `${dbProject[0].title} (Copy)`,
          video_title: dbProject[0].video_title || '',
          userId: session.userId,
          prompt: dbProject[0].prompt,
          staticSubtitle: dbProject[0].staticSubtitle,
          desc: dbProject[0].desc,
          brief: dbProject[0].brief,
          bodytext: dbProject[0].bodytext,
          bodytextLength: dbProject[0].bodytextLength,
          news: dbProject[0].news,
          keepTitle: dbProject[0].keepTitle,
          openAfterGeneration: dbProject[0].openAfterGeneration,
          addTimestampToTitle: dbProject[0].addTimestampToTitle,
          titleFont: dbProject[0].titleFont,
          titleFontSize: dbProject[0].titleFontSize,
          titlePosition: dbProject[0].titlePosition,
          sortOrder: dbProject[0].sortOrder,
          keepClipLength: dbProject[0].keepClipLength,
          clipNum: dbProject[0].clipNum,
          repeatmode: dbProject[0].repeatmode,
          subtitleFont: dbProject[0].subtitleFont,
          subtitleFontSize: dbProject[0].subtitleFontSize,
          subtitlePosition: dbProject[0].subtitlePosition,
          genSubtitle: dbProject[0].genSubtitle,
          genVoice: dbProject[0].genVoice,
          llmProvider: dbProject[0].llmProvider,
          bgmFile: dbProject[0].bgmFile,
          bgmFadeIn: dbProject[0].bgmFadeIn,
          bgmFadeOut: dbProject[0].bgmFadeOut,
          bgmVolume: dbProject[0].bgmVolume,
          commonPrompt: dbProject[0].commonPrompt,
          createdAt: new Date(),
          updatedAt: new Date()
        })
        .returning();

      if (!newProject || newProject.length === 0) {
        console.error(
          '❌ [PROJECT COPY API] Failed to create project in database'
        );
        return error(500, { message: 'Failed to create project in database' });
      }

      // Copy materials from source project to new project
      try {
        const sourceMaterials = await db
          .select()
          .from(material)
          .where(eq(material.projectId, projectId));

        if (sourceMaterials.length > 0) {
          const materialsToInsert = sourceMaterials.map((mat) => ({
            id: nanoid(),
            projectId: newProjectId,
            relativePath: mat.relativePath,
            fileName: mat.fileName,
            fileType: mat.fileType,
            alias: mat.alias,
            isCandidate: mat.isCandidate,
            createdAt: new Date()
          }));

          await db.insert(material).values(materialsToInsert);
          console.log(
            `✅ [PROJECT COPY API] Copied ${sourceMaterials.length} materials to new project`
          );
        }
      } catch (materialsErr) {
        console.warn(
          '⚠️ [PROJECT COPY API] Failed to copy materials, but project was created:',
          materialsErr
        );
        // Don't fail the entire operation if materials copy fails
      }

      console.log('✅ [PROJECT COPY API] Project copied:', newProjectId);

      return json(newProject[0], { status: 201 });
    } catch (fsErr) {
      console.error('❌ [PROJECT COPY API] Failed to copy project:', fsErr);
      return error(500, { message: 'Failed to copy project' });
    }
  } catch (err) {
    console.error('❌ [PROJECT COPY API] Project copy error:', err);
    return error(500, { message: 'Internal server error' });
  }
}

async function copyDirectoryRecursive(source: string, destination: string) {
  const entries = await fs.readdir(source, { withFileTypes: true });

  await fs.mkdir(destination, { recursive: true });

  for (const entry of entries) {
    const srcPath = path.join(source, entry.name);
    const destPath = path.join(destination, entry.name);

    if (entry.isDirectory()) {
      await copyDirectoryRecursive(srcPath, destPath);
    } else {
      await fs.copyFile(srcPath, destPath);
    }
  }
}
