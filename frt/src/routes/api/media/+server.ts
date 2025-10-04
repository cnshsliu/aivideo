import { json, error } from '@sveltejs/kit';
import { readFileSync, readdirSync, statSync } from 'fs';
import { verifySession } from "$lib/server/auth";
import { join } from 'path';

const VAULT_PATH = process.env.AIV_VAULT_FOLDER || './vault';


export async function GET({ url, cookies }) {
  console.log("🍪 [MEDIA API] All cookies object:", cookies);
  console.log("🍪 [MEDIA API] Cookie keys:", Object.keys(cookies.getAll()));
  try {
    const level = url.searchParams.get('level') || 'public';
    const projectId = url.searchParams.get('projectId');
    
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
    
    console.log('📂 [MEDIA API] VAULT_PATH:', VAULT_PATH);
    console.log('📂 [MEDIA API] Current working directory:', process.cwd());
    console.log('📂 [MEDIA API] Level:', level);
    console.log('📂 [MEDIA API] Final media path:', mediaPath);
    
    // Ensure directory exists
    try {
      console.log('🔍 [MEDIA API] Attempting to read directory:', mediaPath);
      const files = readdirSync(mediaPath);
      console.log('📄 [MEDIA API] Files found:', files);
      const mediaFiles = files
        .map(file => {
          try {
            const filePath = join(mediaPath, file);
            const stats = statSync(filePath);
            const ext = file.split('.').pop()?.toLowerCase() || '';
            
            let type = 'unknown';
            if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) {
              type = 'image';
            } else if (['mp4', 'webm', 'avi', 'mov', 'mkv'].includes(ext)) {
              type = 'video';
            } else if (['mp3', 'wav', 'ogg', 'aac'].includes(ext)) {
              type = 'audio';
            }
            
            return {
              name: file,
              type,
              size: stats.size,
              modified: stats.mtime.toISOString(),
              url: `/api/media/file/${level}/${projectId ? `${projectId}/` : ''}${file}`
            };
          } catch (err) {
            console.error(`Error processing file ${file}:`, err);
            return null;
          }
        })
        .filter((item) => item !== null)
        .sort((a, b) => new Date(b.modified).getTime() - new Date(a.modified).getTime());
      
      console.log('✅ [MEDIA API] Processed media files:', mediaFiles.length);
      return json(mediaFiles);
    } catch (err:any) {
      console.log('❌ [MEDIA API] Directory does not exist or cannot be accessed:', err.message);
      // Directory doesn't exist, return empty array
      return json([]);
    }
  } catch (err) {
    console.error('❌ [MEDIA API] Error listing media:', err);
    throw error(500, 'Failed to list media files');
  }
}
