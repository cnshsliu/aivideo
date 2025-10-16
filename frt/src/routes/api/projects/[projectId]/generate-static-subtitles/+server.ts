import { json, error } from '@sveltejs/kit';
import { verifySession } from '$lib/server/auth';
import { db } from '$lib/server/db';
import { project } from '$lib/server/db/schema';
import { eq } from 'drizzle-orm';
import fs from 'fs/promises';
import path from 'path';
import { spawn } from 'child_process';

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

    // Get vault path
    const vaultPath = process.env.AIV_VAULT_FOLDER || './vault';
    const fullVaultPath = path.resolve(vaultPath);
    const userPath = path.join(fullVaultPath, session.username);
    const projectPath = path.join(userPath, folder || selectedProject.name);

    // Check if project folder exists
    try {
      await fs.access(projectPath);
    } catch (err) {
      return error(404, { message: err ? 'Project folder not found' : '' });
    }

    // Save project's prompt field value to project_folder/prompt/prompt.txt
    if (selectedProject.prompt && selectedProject.prompt.trim()) {
      const promptDir = path.join(projectPath, 'prompt');
      await fs.mkdir(promptDir, { recursive: true });
      const promptPath = path.join(promptDir, 'prompt.txt');
      await fs.writeFile(
        promptPath,
        selectedProject.prompt.trim() +
          (selectedProject.commonPrompt
            ? '\n\nYOU MUST:\n' + selectedProject.commonPrompt.trim()
            : '')
      );
      console.log('📝 [STATIC SUBTITLES API] Prompt file created:', promptPath);
    }

    // Compose command for static subtitles generation (only --folder and --gen1)
    const mainDir =
      process.env.PYTHON_GEN_DIR || '/Users/lucas/dev/aivideo/python';
    const mainPyPath = path.join(mainDir, 'main.py');
    const command = `"${mainPyPath}" --folder "${projectPath}" --gen1`;

    console.log('🔧 [STATIC SUBTITLES API] Composed command:', command);

    // Execute command and capture output
    const result = await executeCommandForSubtitles(projectPath, mainDir);

    // Process the result to extract only the subtitles array and join with newlines
    let processedResult = result;
    if (result && result.trim()) {
      const lines = result.trim().split('\n');
      // Find the line containing the array (starts with '[' or '"[')
      const arrayLine = lines.find(
        (line) => line.trim().startsWith('[') || line.trim().startsWith('"[')
      );
      if (arrayLine) {
        try {
          let jsonString = arrayLine.trim();
          // If it starts with '"[', remove the outer quotes (Python repr() output)
          if (jsonString.startsWith('"[') && jsonString.endsWith(']"')) {
            jsonString = jsonString.slice(1, -1);
          }
          // Convert Python single quotes to double quotes for valid JSON
          jsonString = jsonString.replace(/'/g, '"');
          const subtitlesArray = JSON.parse(jsonString);
          processedResult = subtitlesArray.join('\n');
        } catch (parseError: unknown) {
          const errorMessage =
            parseError instanceof Error
              ? parseError.message
              : String(parseError);
          console.error(errorMessage);
          console.error(
            '❌ [STATIC SUBTITLES API] Failed to parse subtitles array:',
            parseError
          );
          console.error('❌ [STATIC SUBTITLES API] Array line was:', arrayLine);
          // Fallback to original result if parsing fails
        }
      }
    }

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

    return json({ success: true, result });
  } catch (err) {
    console.error(
      '❌ [STATIC SUBTITLES API] Static subtitles generation error:',
      err
    );
    return error(500, { message: 'Internal server error' });
  }
}

async function executeCommandForSubtitles(
  projectPath: string,
  cwd: string
): Promise<string> {
  return new Promise<string>((resolve, reject) => {
    console.log(
      '🚀 [STATIC SUBTITLES API] Executing Python script for project:',
      projectPath
    );

    // Use Python executable directly with script path and arguments
    const pythonCmd = '/Users/lucas/miniconda3/envs/aivideo/bin/python';
    const scriptPath = '/Users/lucas/dev/aivideo/python/main.py';
    const args = [scriptPath, '--folder', projectPath, '--gen1'];

    console.log('🐍 [STATIC SUBTITLES API] Python command:', pythonCmd);
    console.log('📜 [STATIC SUBTITLES API] Script args:', args);

    // Execute command
    const child = spawn(pythonCmd, args, {
      cwd: cwd
    });

    let stdout = '';
    let stderr = '';

    // Capture stdout
    child.stdout.on('data', (data) => {
      stdout += data.toString();
      console.log(`[PYTHON STDOUT] ${data}`);
    });

    // Capture stderr
    child.stderr.on('data', (data) => {
      stderr += data.toString();
      console.log(`[PYTHON STDERR] ${data}`);
    });

    // Handle process completion
    child.on('close', (code) => {
      console.log(`🎬 [STATIC SUBTITLES API] Process exited with code ${code}`);
      console.log(`📄 [STATIC SUBTITLES API] STDOUT length: ${stdout.length}`);
      console.log(`📄 [STATIC SUBTITLES API] STDERR length: ${stderr.length}`);

      if (stderr) {
        console.error(`❌ [STATIC SUBTITLES API] STDERR content:`, stderr);
      }

      if (code === 0) {
        resolve(stdout);
      } else {
        const errorMsg = `Process failed with code ${code}. STDOUT: ${stdout || 'empty'}. STDERR: ${stderr || 'empty'}`;
        console.error(`❌ [STATIC SUBTITLES API] ${errorMsg}`);
        reject(new Error(errorMsg));
      }
    });

    // Handle process error
    child.on('error', (err) => {
      console.error('❌ [STATIC SUBTITLES API] Process error:', err);
      reject(err);
    });
  });
}
