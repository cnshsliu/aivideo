import { json, error } from '@sveltejs/kit';
import { spawn } from 'child_process';
import { promises as fs } from 'fs';
import path from 'path';
import { verifySession } from '$lib/server/auth';
import { db } from '$lib/server/db';
import { project } from '$lib/server/db/schema';
import { eq, and } from 'drizzle-orm';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, params, cookies }) => {
  try {
    console.log(
      '🎬 [VIDEO PUBLISH API] POST request to publish video for project:',
      params.projectId
    );

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log('❌ [VIDEO PUBLISH API] Unauthorized access attempt');
      return error(401, { message: 'Unauthorized' });
    }

    const { projectId } = params;

    // Fetch project from database
    const dbProject = await db
      .select()
      .from(project)
      .where(and(eq(project.id, projectId), eq(project.userId, session.userId)))
      .limit(1);

    if (!dbProject || dbProject.length === 0) {
      return error(404, { message: 'Project not found' });
    }

    const selectedProject = dbProject[0];

    // Check AIV_PUBLISH_FOLDER environment variable, default to ~/dev/aivideo/publish
    const publishFolder =
      process.env.AIV_PUBLISH_FOLDER ||
      `${process.env.HOME}/dev/aivideo/publish`;

    // Ensure publish folder exists
    try {
      await fs.mkdir(publishFolder, { recursive: true });
    } catch (error) {
      console.error('Failed to create publish folder:', error);
      return json(
        { error: 'Failed to create publish folder' },
        { status: 500 }
      );
    }

    // Create JSON filename
    const jsonFilename = `${selectedProject.name}.json`;
    const jsonFilePath = path.join(publishFolder, jsonFilename);

    // Check if file exists and backup if needed
    try {
      await fs.access(jsonFilePath);
      // File exists, create backup
      const backupTimestamp = new Date(Date.now() - 10000)
        .toISOString()
        .replace(/[:.]/g, '-');
      const backupFilename = `${selectedProject.name}_${backupTimestamp}.json`;
      const backupFilePath = path.join(publishFolder, backupFilename);

      await fs.rename(jsonFilePath, backupFilePath);
      console.log(`Backed up existing file to: ${backupFilename}`);
    } catch {
      // File doesn't exist, no backup needed
    }

    // Get the full path to the generated video
    const vaultPath = process.env.AIV_VAULT_FOLDER || './vault';
    const fullVaultPath = path.resolve(vaultPath);
    const userPath = path.join(fullVaultPath, session.username);
    const projectPath = path.join(userPath, selectedProject.name);
    const videoPath = path.join(projectPath, 'output', 'output.mp4');

    // Create JSON content
    const jsonContent = {
      video: videoPath,
      desc: selectedProject.desc || '',
      brief: selectedProject.brief || ''
    };

    // Write JSON file
    try {
      await fs.writeFile(
        jsonFilePath,
        JSON.stringify(jsonContent, null, 2),
        'utf-8'
      );
      console.log(`Created publish file: ${jsonFilePath}`);
    } catch (error) {
      console.error('Failed to write JSON file:', error);
      return json({ error: 'Failed to write JSON file' }, { status: 500 });
    }

    // Execute the wxvPost command
    const command = `npx tsx ~/dev/aivideo/wxvPost/wxvPost.ts --json ${jsonFilename}`;

    return new Promise((resolve) => {
      const child = spawn(command, [], {
        shell: true,
        cwd: publishFolder,
        stdio: ['inherit', 'inherit', 'inherit']
      });

      child.on('close', (code) => {
        if (code === 0) {
          resolve(
            json({
              success: true,
              message: 'Video published successfully',
              jsonFile: jsonFilePath,
              videoPath
            })
          );
        } else {
          resolve(
            json(
              {
                error: `Publish command failed with code ${code}`,
                jsonFile: jsonFilePath
              },
              { status: 500 }
            )
          );
        }
      });

      child.on('error', (error) => {
        console.error('Command execution error:', error);
        resolve(
          json(
            {
              error: 'Command execution failed',
              jsonFile: jsonFilePath
            },
            { status: 500 }
          )
        );
      });
    });
  } catch (error) {
    console.error('Publish API error:', error);
    return json({ error: 'Internal server error' }, { status: 500 });
  }
};
