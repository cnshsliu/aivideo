import { error } from "@sveltejs/kit";
import { readFileSync, statSync, readdirSync } from "fs";
import { join } from "path";
import { verifySession } from "$lib/server/auth";

const VAULT_PATH = process.env.AIV_VAULT_FOLDER || "./vault";

export async function GET({ params, cookies }) {
  try {
    const pathParts = params.path.split("/");
    const level = pathParts[0];
    const projectId = pathParts.length > 2 ? pathParts[1] : null;
    const filename = pathParts[pathParts.length - 1];

    let mediaPath = join(VAULT_PATH, "public", "media");

    if (level === "user") {
      const session = await verifySession(cookies);
      if (!session) {
        throw error(401, "Authentication required");
      }
      mediaPath = join(VAULT_PATH, session.username, "media");
    } else if (level === "project") {
      if (!projectId) {
        throw error(400, "Invalid path");
      }
      const session = await verifySession(cookies);
      if (!session) {
        throw error(401, "Authentication required");
      }
      mediaPath = join(VAULT_PATH, session.username, projectId);
    } else if (level === "public" && pathParts[1] === "bgm") {
      // Handle public BGM files
      mediaPath = join(VAULT_PATH, "public", "bgm");
      
      console.log("BGM path handling:", { pathParts, mediaPath, length: pathParts.length });
      
      // If only "public/bgm" path parts, list the files
      if (pathParts.length === 2) {
        try {
          const files = readdirSync(mediaPath);
          console.log("Files in BGM directory:", files);
          const bgmFiles = files.filter((file) => {
            const ext = file.split(".").pop()?.toLowerCase() || "";
            return ["mp3", "wav", "ogg", "aac", "flac", "m4a"].includes(ext);
          });
          console.log("Filtered BGM files:", bgmFiles);
          return new Response(JSON.stringify(bgmFiles), {
            headers: {
              "Content-Type": "application/json",
            },
          });
        } catch (err) {
          console.error("Error listing BGM files:", err);
          return new Response(JSON.stringify([]), {
            headers: {
              "Content-Type": "application/json",
            },
          });
        }
      } else {
        // For BGM files, the filename is the last part of the path
        const bgmFilename = pathParts[pathParts.length - 1];
        const filePath = join(mediaPath, bgmFilename);
        
        // Check if file exists
        try {
          const stats = statSync(filePath);
          const fileContent = readFileSync(filePath);

          // Determine content type for audio files
          const ext = bgmFilename.split(".").pop()?.toLowerCase() || "";
          let contentType = "application/octet-stream";

          if (ext === "mp3") contentType = "audio/mpeg";
          else if (ext === "wav") contentType = "audio/wav";
          else if (ext === "ogg") contentType = "audio/ogg";
          else if (ext === "aac") contentType = "audio/aac";
          else if (ext === "flac") contentType = "audio/flac";
          else if (ext === "m4a") contentType = "audio/mp4";

          return new Response(fileContent, {
            headers: {
              "Content-Type": contentType,
              "Content-Length": stats.size.toString(),
              "Cache-Control": "public, max-age=31536000",
            },
          });
        } catch (err) {
          console.error("Error serving BGM file:", err);
          throw error(404, "File not found");
        }
      }
    }

    const filePath = join(mediaPath, filename);

    // Check if file exists
    try {
      const stats = statSync(filePath);
      const fileContent = readFileSync(filePath);

      // Determine content type
      const ext = filename.split(".").pop()?.toLowerCase() || "";
      let contentType = "application/octet-stream";

      if (["jpg", "jpeg"].includes(ext)) contentType = "image/jpeg";
      else if (ext === "png") contentType = "image/png";
      else if (ext === "gif") contentType = "image/gif";
      else if (ext === "webp") contentType = "image/webp";
      else if (ext === "mp4") contentType = "video/mp4";
      else if (ext === "webm") contentType = "video/webm";
      else if (ext === "avi") contentType = "video/x-msvideo";
      else if (ext === "mov") contentType = "video/quicktime";
      else if (ext === "mkv") contentType = "video/x-matroska";
      else if (ext === "mp3") contentType = "audio/mpeg";
      else if (ext === "wav") contentType = "audio/wav";
      else if (ext === "ogg") contentType = "audio/ogg";
      else if (ext === "aac") contentType = "audio/aac";

      return new Response(fileContent, {
        headers: {
          "Content-Type": contentType,
          "Content-Length": stats.size.toString(),
          "Cache-Control": "public, max-age=31536000",
        },
      });
    } catch (err) {
      throw error(404, "File not found");
    }
  } catch (err) {
    console.error("Error serving media file:", err);
    throw error(500, "Failed to serve file");
  }
}
