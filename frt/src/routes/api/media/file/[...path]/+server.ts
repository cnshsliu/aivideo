import { error } from "@sveltejs/kit";
import { readFileSync, statSync } from "fs";
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
