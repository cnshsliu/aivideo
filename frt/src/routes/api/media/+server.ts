import { json, error, type Cookies } from '@sveltejs/kit';
import { readdirSync, statSync } from 'fs';
import fs from 'fs/promises';
import { verifySession } from '$lib/server/auth';
import { join } from 'path';

const VAULT_PATH = process.env.AIV_VAULT_FOLDER || './vault';

export async function GET({ url, cookies }: { url: URL; cookies: Cookies }) {
  console.log('🍪 [MEDIA API] All cookies object:', cookies);
  console.log('🍪 [MEDIA API] Cookie keys:', Object.keys(cookies.getAll()));
  try {
    const level = url.searchParams.get('level') || 'public';
    const projectId = url.searchParams.get('projectId');
    const folder = url.searchParams.get('folder') || '';

    let mediaPath = join(VAULT_PATH, 'public', 'media');

    if (level === 'user') {
      const session = await verifySession(cookies);
      if (!session) {
        console.log('❌ [MEDIA API] No session found for user-level access');
        throw error(401, 'Authentication required for user-level media');
      }
      mediaPath = join(VAULT_PATH, session.username, 'media');
      console.log('👤 [MEDIA API] User media path:', mediaPath);
    } else if (level === 'project') {
      if (!projectId) {
        throw error(400, 'Project ID required for project-level media');
      }
      const session = await verifySession(cookies);
      if (!session) {
        console.log('❌ [MEDIA API] No session found for project-level access');
        throw error(401, 'Authentication required for project-level media');
      }
      mediaPath = join(VAULT_PATH, session.username, projectId, 'media');
      console.log('📁 [MEDIA API] Project media path:', mediaPath);
    }

    // Apply folder path if specified
    const currentPath = folder ? join(mediaPath, folder) : mediaPath;

    console.log('📂 [MEDIA API] VAULT_PATH:', VAULT_PATH);
    console.log('📂 [MEDIA API] Current working directory:', process.cwd());
    console.log('📂 [MEDIA API] Level:', level);
    console.log('📂 [MEDIA API] Folder:', folder);
    console.log('📂 [MEDIA API] Final media path:', currentPath);

    // Ensure directory exists
    try {
      console.log('🔍 [MEDIA API] Attempting to read directory:', currentPath);
      const items = readdirSync(currentPath);
      console.log('📄 [MEDIA API] Items found:', items);

      const mediaItems = [];
      const folders = [];
      const files = [];

      for (const item of items) {
        try {
          const itemPath = join(currentPath, item);
          const stats = statSync(itemPath);

          if (stats.isDirectory()) {
            folders.push({
              name: item,
              type: 'folder',
              size: 0,
              modified: stats.mtime.toISOString(),
              url: null
            });
          } else {
            const ext = item.split('.').pop()?.toLowerCase() || '';

            let type = 'unknown';
            if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) {
              type = 'image';
            } else if (['mp4', 'webm', 'avi', 'mov', 'mkv'].includes(ext)) {
              type = 'video';
            } else if (['mp3', 'wav', 'ogg', 'aac'].includes(ext)) {
              type = 'audio';
            }

            // Only include image and video files, filter out audio and unknown files
            if (type === 'image' || type === 'video') {
              const relativePath = folder ? `${folder}/${item}` : item;
              files.push({
                name: item,
                type,
                size: stats.size,
                modified: stats.mtime.toISOString(),
                url: `/api/media/file/${level}/${projectId ? `${projectId}/` : ''}${relativePath}`
              });
            }
          }
        } catch (err) {
          console.error(`Error processing item ${item}:`, err);
        }
      }

      // Combine folders and files, sort by modification time
      mediaItems.push(...folders, ...files);
      mediaItems.sort(
        (a, b) =>
          new Date(b.modified).getTime() - new Date(a.modified).getTime()
      );

      console.log('✅ [MEDIA API] Processed media items:', mediaItems.length);
      return json(mediaItems);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      console.log(
        '❌ [MEDIA API] Directory does not exist or cannot be accessed:',
        message
      );
      // Directory doesn't exist, return empty array
      return json([]);
    }
  } catch (err) {
    console.error('❌ [MEDIA API] Error listing media:', err);
    throw error(500, 'Failed to list media files');
  }
}

export async function POST({
  request,
  cookies
}: {
  request: Request;
  cookies: Cookies;
}) {
  try {
    console.log('📁 [MEDIA API] POST request received');

    const session = await verifySession(cookies);
    if (!session) {
      console.log('❌ [MEDIA API] No session found for folder creation');
      throw error(401, 'Authentication required');
    }

    const { level, folderName, parentFolder } = await request.json();
    console.log('📋 [MEDIA API] Create folder details:', { level, folderName, parentFolder });

    if (!level || !['public', 'user'].includes(level)) {
      throw error(400, 'Invalid level. Must be "public" or "user"');
    }

    if (!folderName || typeof folderName !== 'string' || folderName.trim() === '') {
      throw error(400, 'Folder name is required and cannot be empty');
    }

    // Validate folder name (no special characters that could cause issues)
    if (/[<>:"/\\|?*]/.test(folderName)) {
      throw error(400, 'Folder name contains invalid characters');
    }

    let mediaPath = join(VAULT_PATH, 'public', 'media');
    if (level === 'user') {
      mediaPath = join(VAULT_PATH, session.username, 'media');
    }

    const folderPath = parentFolder ? join(mediaPath, parentFolder, folderName) : join(mediaPath, folderName);

    console.log('📂 [MEDIA API] Creating folder at:', folderPath);

    try {
      await fs.mkdir(folderPath, { recursive: true });
      console.log('✅ [MEDIA API] Folder created successfully:', folderName);
      return json({ success: true, folderName, path: parentFolder ? `${parentFolder}/${folderName}` : folderName });
    } catch (err) {
      console.error(`❌ [MEDIA API] Failed to create folder ${folderName}:`, err);
      throw error(500, 'Failed to create folder');
    }
  } catch (err) {
    console.error('❌ [MEDIA API] Error creating folder:', String(err));
    if (err instanceof Error && 'status' in err) {
      throw err;
    }
    throw error(500, 'Failed to create folder');
  }
}

export async function PUT({
  request,
  cookies
}: {
  request: Request;
  cookies: Cookies;
}) {
  try {
    console.log('✏️ [MEDIA API] PUT request received');

    const session = await verifySession(cookies);
    if (!session) {
      console.log('❌ [MEDIA API] No session found for rename operation');
      throw error(401, 'Authentication required');
    }

    const { level, oldName, newName, folderPath } = await request.json();
    console.log('📋 [MEDIA API] Rename details:', { level, oldName, newName, folderPath });

    if (!level || !['public', 'user'].includes(level)) {
      throw error(400, 'Invalid level. Must be "public" or "user"');
    }

    if (!oldName || !newName || typeof oldName !== 'string' || typeof newName !== 'string') {
      throw error(400, 'Both oldName and newName are required and must be strings');
    }

    if (oldName.trim() === '' || newName.trim() === '') {
      throw error(400, 'Names cannot be empty');
    }

    // Validate new name (no special characters that could cause issues)
    if (/[<>:"/\\|?*]/.test(newName)) {
      throw error(400, 'New name contains invalid characters');
    }

    let mediaPath = join(VAULT_PATH, 'public', 'media');
    if (level === 'user') {
      mediaPath = join(VAULT_PATH, session.username, 'media');
    }

    // Apply folder path if specified
    const basePath = folderPath ? join(mediaPath, folderPath) : mediaPath;

    const oldPath = join(basePath, oldName);
    let finalNewName = newName.trim();

    // Check if the new name already exists and add "-copy" suffix if needed
    const newPath = join(basePath, finalNewName);
    try {
      await fs.access(newPath);
      // File exists, add "-copy" suffix
      const extIndex = finalNewName.lastIndexOf('.');
      if (extIndex > 0) {
        const nameWithoutExt = finalNewName.substring(0, extIndex);
        const ext = finalNewName.substring(extIndex);
        finalNewName = `${nameWithoutExt}-copy${ext}`;
      } else {
        finalNewName = `${finalNewName}-copy`;
      }
    } catch {
      // File doesn't exist, use the name as is
    }

    const finalNewPath = join(basePath, finalNewName);

    console.log('📂 [MEDIA API] Rename path:', { oldPath, finalNewPath });

    try {
      await fs.rename(oldPath, finalNewPath);
      console.log('✅ [MEDIA API] Renamed file:', oldName, 'to', finalNewName);
      return json({
        success: true,
        oldName,
        newName: finalNewName,
        finalName: finalNewName
      });
    } catch (err) {
      console.error(`❌ [MEDIA API] Failed to rename ${oldName} to ${finalNewName}:`, err);
      throw error(500, 'Failed to rename file');
    }
  } catch (err) {
    console.error('❌ [MEDIA API] Error renaming media:', String(err));
    if (err instanceof Error && 'status' in err) {
      throw err;
    }
    throw error(500, 'Failed to rename media file');
  }
}

export async function DELETE({
  request,
  cookies
}: {
  request: Request;
  cookies: Cookies;
}) {
  try {
    console.log('🗑️ [MEDIA API] DELETE request received');

    const session = await verifySession(cookies);
    if (!session) {
      console.log('❌ [MEDIA API] No session found for delete operation');
      throw error(401, 'Authentication required');
    }

    const { level, files, folders } = await request.json();
    console.log('📋 [MEDIA API] Delete details:', { level, files, folders });

    if (!level || !['public', 'user'].includes(level)) {
      throw error(400, 'Invalid level. Must be "public" or "user"');
    }

    let mediaPath = join(VAULT_PATH, 'public', 'media');
    if (level === 'user') {
      mediaPath = join(VAULT_PATH, session.username, 'media');
    }

    console.log('📂 [MEDIA API] Delete path:', mediaPath);

    const deletedFiles = [];
    const failedFiles = [];
    const deletedFolders = [];
    const failedFolders = [];

    // Delete files
    if (Array.isArray(files)) {
      for (const fileName of files) {
        try {
          const filePath = join(mediaPath, fileName);
          await fs.unlink(filePath);
          deletedFiles.push(fileName);
          console.log('✅ [MEDIA API] Deleted file:', fileName);
        } catch (err) {
          console.error(`❌ [MEDIA API] Failed to delete ${fileName}:`, err);
          failedFiles.push(fileName);
        }
      }
    }

    // Delete folders (only if empty)
    if (Array.isArray(folders)) {
      for (const folderName of folders) {
        try {
          const folderPath = join(mediaPath, folderName);
          await fs.rmdir(folderPath);
          deletedFolders.push(folderName);
          console.log('✅ [MEDIA API] Deleted folder:', folderName);
        } catch (err) {
          console.error(`❌ [MEDIA API] Failed to delete folder ${folderName}:`, err);
          failedFolders.push(folderName);
        }
      }
    }

    console.log('🎉 [MEDIA API] Delete operation completed');
    return json({
      success: true,
      deleted: { files: deletedFiles, folders: deletedFolders },
      failed: { files: failedFiles, folders: failedFolders }
    });
  } catch (err) {
    console.error('❌ [MEDIA API] Error deleting media:', String(err));
    if (err instanceof Error && 'status' in err) {
      throw err;
    }
    throw error(500, 'Failed to delete media files');
  }
}
