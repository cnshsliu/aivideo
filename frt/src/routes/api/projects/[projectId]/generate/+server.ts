import { json, error } from '@sveltejs/kit';
import { verifySession } from '$lib/server/auth';
import { db } from '$lib/server/db';
import { project, material } from '$lib/server/db/schema';
import { eq, and } from 'drizzle-orm';
import fs from 'fs/promises';
import fsSync from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import type { Project } from '$lib/server/db/schema';

// Store active child processes for cancellation
const activeProcesses = new Map<string, { child: any; logStream: any }>();

export async function POST({ params, cookies }) {
  try {
    console.log(
      '🎬 [VIDEO GENERATE API] POST request to generate video for project:',
      params.projectId
    );

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log('❌ [VIDEO GENERATE API] Unauthorized access attempt');
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

    const selectedProject = dbProject[0];

    // Get vault path
    const vaultPath = process.env.AIV_VAULT_FOLDER || './vault';
    const fullVaultPath = path.resolve(vaultPath);
    const userPath = path.join(fullVaultPath, session.username);
    const projectPath = path.join(userPath, selectedProject.name);
    const logPath = path.join(projectPath, 'log.txt');

    // Check if project folder exists
    try {
      await fs.access(projectPath);
    } catch (err) {
      return error(404, {
        message: err ? `Project folder ${projectPath}  not found` : ''
      });
    }

    // Create progress record
    await db
      .update(project)
      .set({
        progressStep: 'preparing',
        progressCommand: '',
        progressResult: '',
        progressLog: logPath,
        progressCreatedAt: new Date(),
        progressUpdatedAt: new Date()
      })
      .where(eq(project.id, projectId));

    // Run the video generation process
    await prepareAndRunGeneration(selectedProject, projectPath);

    console.log('✅ [VIDEO GENERATE API] Video generation started:', projectId);

    return json({ success: true });
  } catch (err) {
    console.error('❌ [VIDEO GENERATE API] Video generation error:', err);
    return error(500, { message: 'Internal server error' });
  }
}

export async function DELETE({ params, cookies }) {
  try {
    console.log(
      '🛑 [VIDEO GENERATE API] DELETE request to cancel video generation for project:',
      params.projectId
    );

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log('❌ [VIDEO GENERATE API] Unauthorized access attempt');
      return error(401, { message: 'Unauthorized' });
    }

    const { projectId } = params;

    // Check if there's an active process for this project
    const activeProcess = activeProcesses.get(projectId);
    if (!activeProcess) {
      console.log('ℹ️ [VIDEO GENERATE API] No active process found for project:', projectId);
      return json({ success: true, message: 'No active process to cancel' });
    }

    const { child, logStream } = activeProcess;

    // Kill the child process
    try {
      child.kill('SIGTERM');
      console.log('✅ [VIDEO GENERATE API] Sent SIGTERM to child process for project:', projectId);
    } catch (killErr) {
      console.error('❌ [VIDEO GENERATE API] Error killing child process:', killErr);
      // Try force kill
      try {
        child.kill('SIGKILL');
        console.log('✅ [VIDEO GENERATE API] Sent SIGKILL to child process for project:', projectId);
      } catch (forceKillErr) {
        console.error('❌ [VIDEO GENERATE API] Error force killing child process:', forceKillErr);
      }
    }

    // Close the log stream
    try {
      logStream.end();
      console.log('✅ [VIDEO GENERATE API] Closed log stream for project:', projectId);
    } catch (streamErr) {
      console.error('❌ [VIDEO GENERATE API] Error closing log stream:', streamErr);
    }

    // Remove from active processes
    activeProcesses.delete(projectId);

    // Update project status to error (cancelled)
    await db
      .update(project)
      .set({
        progressStep: 'error',
        progressUpdatedAt: new Date()
      })
      .where(eq(project.id, projectId));

    console.log('✅ [VIDEO GENERATE API] Video generation cancelled for project:', projectId);

    return json({ success: true, message: 'Video generation cancelled' });
  } catch (err) {
    console.error('❌ [VIDEO GENERATE API] Video generation cancellation error:', err);
    return error(500, { message: 'Internal server error' });
  }
}

async function prepareAndRunGeneration(
  theProject: Project,
  projectPath: string
) {
  const projectId = theProject.id;
  try {
    // Step 1: Preparing
    console.log(
      '🔄 [VIDEO GENERATE] Preparing step for project:',
      theProject.id
    );

    // Update progress to preparing
    await db
      .update(project)
      .set({
        progressStep: 'preparing',
        progressUpdatedAt: new Date()
      })
      .where(eq(project.id, projectId));

    // 2.1 Copy project.prompt to PROJ_DIR/prompt/prompt.md
    if (theProject.prompt && theProject.prompt!.trim()) {
      const promptDir = path.join(projectPath, 'prompt');
      await fs.mkdir(promptDir, { recursive: true });
      const promptPath = path.join(promptDir, 'prompt.md');
      await fs.writeFile(promptPath, theProject.prompt!.trim());
      console.log('📝 [VIDEO GENERATE] Prompt file created:', promptPath);
    }

    // 2.2 Copy project.static_subtitles to PROJ_DIR/static_subtitles.txt
    if (theProject.staticSubtitle && theProject.staticSubtitle!.trim()) {
      const staticSubtitlePath = path.join(
        projectPath,
        'subtitle',
        'static_subtitles.txt'
      );
      await fs.writeFile(staticSubtitlePath, theProject.staticSubtitle!.trim());
      console.log(
        '📝 [VIDEO GENERATE] Static subtitle file created:',
        staticSubtitlePath
      );
    }

    // 2.3 Copy project materials files to PROJ_DIR/media
    const materials = await db
      .select()
      .from(material)
      .where(and(eq(material.projectId, theProject.id), eq(material.isCandidate, true)));

    const mediaDir = path.join(projectPath, 'media');
    await fs.mkdir(mediaDir, { recursive: true });

    // Clear existing files in mediaDir
    const existingFiles = await fs.readdir(mediaDir);
    for (const file of existingFiles) {
      const filePath = path.join(mediaDir, file);
      const stat = await fs.stat(filePath);
      if (stat.isFile()) {
        await fs.unlink(filePath);
      }
    }

    if (materials.length > 0) {
      const mediaDir = path.join(projectPath, 'media');
      await fs.mkdir(mediaDir, { recursive: true });

      console.log('VAULT ENV VLAUE', process.env.AIV_VAULT_FOLDER);
      for (const mat of materials) {
        const vaultPath = process.env.AIV_VAULT_FOLDER || './vault';
        const sourcePath = path.join(vaultPath, mat.relativePath);

        // Get file extension from source file
        const sourceExt = path.extname(mat.fileName);

        // Use alias as filename, removing any existing extension and adding source file's extension
        let destFileName = mat.alias || mat.fileName;
        if (path.extname(destFileName) !== sourceExt) {
          destFileName =
            path.basename(destFileName, path.extname(destFileName)) + sourceExt;
        }

        const destPath = path.join(mediaDir, destFileName);

        try {
          await fs.copyFile(sourcePath, destPath);
          console.log('📁 [VIDEO GENERATE] Copied material:', destFileName);
        } catch (copyErr) {
          console.error(
            '❌ [VIDEO GENERATE] Error copying material:',
            destFileName,
            copyErr
          );
        }
      }
    }

    // 2.4 Compose command string
    const command = composeCommand(theProject, projectPath);
    console.log('🔧 [VIDEO GENERATE] Composed command:', command);

    // Update progress with command
    await db
      .update(project)
      .set({
        progressCommand: command,
        progressUpdatedAt: new Date()
      })
      .where(eq(project.id, projectId));

    // Step 2: Running
    console.log('🏃 [VIDEO GENERATE] Running step for project:', theProject.id);

    // Update progress to running
    await db
      .update(project)
      .set({
        progressStep: 'running',
        progressUpdatedAt: new Date()
      })
      .where(eq(project.id, projectId));

    // Execute command and redirect logs
    const logPath = path.join(projectPath, 'log.txt');
    console.log('Logpath:', logPath);
    await executeCommandAndLog(command, logPath, projectId);
  } catch (err) {
    console.error('❌ [VIDEO GENERATE] Error in prepareAndRunGeneration:', err);
    // Update progress with error
    await db
      .update(project)
      .set({
        progressStep: 'complete',
        progressUpdatedAt: new Date()
      })
      .where(eq(project.id, projectId));
  }
}

function composeCommand(project: Project, projectPath: string): string {
  // Base command with absolute path to main.py
  const mainDir =
    process.env.PYTHON_GEN_DIR || '/Users/lucas/dev/aivideo/python';
  const mainPyPath = path.join(mainDir, 'main.py');
  let command = `"${mainPyPath}" --folder "${projectPath}"`;

  // Add LLM provider
  if (project.llmProvider) {
    command += ` --llm-provider ${project.llmProvider}`;
  }

  // Add title options
  if (project.titleFontSize) {
    command += ` --title-font-size ${project.titleFontSize}`;
  }

  if (project.titlePosition) {
    command += ` --title-position ${project.titlePosition}`;
  }

  if (project.titleFont) {
    command += ` --title-font "${project.titleFont}"`;
  }

  if (project.keepTitle) {
    command += ' --keep-title';
  }

  if (project.video_title) {
    command += ` --title "${project.video_title}"`;
  }

  if (project.subtitlePosition) {
    command += ` --subtitle-position ${project.subtitlePosition}`;
  }

  // Add background music
  if (project.bgmFile) {
    command += ` --mp3 "${path.join(process.env.AIV_VAULT_FOLDER || './vault', 'public', 'bgm', project.bgmFile)}"`;
  }

  if (project.bgmFadeIn) {
    command += ` --bgm-fade-in ${project.bgmFadeIn}`;
  }
  if (project.bgmFadeOut) {
    command += ` --bgm-fade-out ${project.bgmFadeOut}`;
  }
  if (project.bgmVolume) {
    command += ` --bgm-volume ${project.bgmVolume}`;
  }

  if (project.genSubtitle) {
    command += ` --gen-subtitle`;
  } else {
    const staticSubtitlePath = path.join(
      projectPath,
      'subtitle',
      'static_subtitles.txt'
    );
    command += ` --text "${staticSubtitlePath}"`;
  }
  // Add text file path

  const generated_audio_mp3_file = path.join(
    projectPath,
    'generated_audio.mp3'
  );
  // Add voice generation
  if (project.genVoice) {
    command += ' --gen-voice';
  } else if (!fsSync.existsSync(generated_audio_mp3_file)) {
    command += ' --gen-voice';
  }

  // Add open flag
  if (project.openAfterGeneration) {
    command += ' --open';
  }

  // Add timestamp to title
  if (project.addTimestampToTitle) {
    command += ' --title-timestamp';
  }

  console.log(command);
  return command;
}

async function executeCommandAndLog(
  command: string,
  logPath: string,
  projectId: string
): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    console.log('🚀 [VIDEO GENERATE] Log Path:', logPath);
    console.log('🚀 [VIDEO GENERATE] Executing command:', command);

    // Split command into parts for spawn, handling quoted arguments properly
    const args = command.match(/(?:[^\s"]+|"[^"]*")+/g) || [];
    const cmd = '/Users/lucas/miniconda3/envs/aivideo/bin/python';
    // Remove quotes from arguments
    const cleanArgs = args.map((arg) => arg.replace(/^"(.*)"$/, '$1'));

    // Create log file write stream (overwrite mode to clear previous logs)
    const logStream = fsSync.createWriteStream(logPath, { flags: 'w' });

    // Execute command with the correct working directory
    const mainDir =
      process.env.PYTHON_GEN_DIR || '/Users/lucas/dev/aivideo/python';
    console.log('📂 [VIDEO GENERATE] main.py is in:', mainDir);

    // Use the conda Python interpreter directly
    const child = spawn(cmd, cleanArgs, {
      cwd: mainDir // Python directory where main.py is located
    });

    // Store the child process and log stream for potential cancellation
    activeProcesses.set(projectId, { child, logStream });

    // Write stdout and stderr to log file
    child.stdout.pipe(logStream);
    child.stderr.pipe(logStream);

    // Also log to console
    // child.stdout.on('data', (data) => {
    //   console.log(`[PYTHON STDOUT] ${data}`);
    // });
    //
    // child.stderr.on('data', (data) => {
    //   console.log(`[FYTHON STDERR] ${data}`);
    // });

    // Handle process completion
    child.on('close', async (code) => {
      console.log(`🎬 [VIDEO GENERATE] Process exited with code ${code}`);

      // Remove from active processes
      activeProcesses.delete(projectId);

      try {
        // Close log stream
        logStream.end();

        // Update progress to complete
        await db
          .update(project)
          .set({
            progressStep: 'complete',
            progressLog: logPath,
            progressUpdatedAt: new Date()
          })
          .where(eq(project.id, projectId));

        // Try to find the result video file
        try {
          const outputDir = path.join(path.dirname(logPath), 'output');
          const files = await fs.readdir(outputDir);
          const videoFiles = files.filter(
            (file) =>
              file.endsWith('.mp4') ||
              file.endsWith('.mov') ||
              file.endsWith('.avi')
          );

          if (videoFiles.length > 0) {
            const resultPath = path.join(outputDir, videoFiles[0]);
            await db
              .update(project)
              .set({
                progressResult: resultPath,
                progressUpdatedAt: new Date()
              })
              .where(eq(project.id, projectId));
          }
        } catch (fileErr) {
          console.warn(
            '⚠️ [VIDEO GENERATE] Could not find result video file:',
            fileErr
          );
        }

        resolve();
      } catch (err) {
        console.error('❌ [VIDEO GENERATE] Error updating progress:', err);
        reject(err);
      }
    });

    // Handle process error
    child.on('error', async (err) => {
      console.error('❌ [VIDEO GENERATE] Process error:', err);

      // Remove from active processes
      activeProcesses.delete(projectId);

      try {
        // Update progress with error
        await db
          .update(project)
          .set({
            progressStep: 'error',
            progressLog: logPath,
            progressUpdatedAt: new Date()
          })
          .where(eq(project.id, projectId));
      } catch (dbErr) {
        console.error('❌ [VIDEO GENERATE] Error updating progress:', dbErr);
      }

      reject(err);
    });
  });
}
