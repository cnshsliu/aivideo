import { json, error, type RequestEvent } from "@sveltejs/kit";
import { verifySession } from "$lib/server/auth";
import { db } from "$lib/server/db";
import { material, project } from "$lib/server/db/schema";
import fs from "fs/promises";
import path from "path";
import { nanoid } from "nanoid";
import { eq, and } from "drizzle-orm";

export async function POST({ request, cookies }: RequestEvent) {
  try {
    console.log("📤 [MEDIA UPLOAD] POST request received");

    // Verify user session for user and project level uploads
    const formData = await request.formData();
    const level = formData.get("level") as string;
    const file = formData.get("file") as File;
    const projectId = formData.get("projectId") as string;

    console.log("📋 [MEDIA UPLOAD] Upload details:", {
      level,
      fileName: file?.name,
      fileSize: file?.size,
      projectId: projectId || "none"
    });

    // Validate inputs
    if (!file) {
      return error(400, { message: "No file provided" });
    }

    if (!level || !["public", "user", "project"].includes(level)) {
      return error(400, { message: "Invalid upload level. Must be 'public', 'user', or 'project'" });
    }

    // Get vault path
    const vaultPath = process.env.AIV_VAULT_FOLDER || "./vault";

    let uploadPath: string = "";
    let session = null;

    if (level === "public") {
      // Public uploads do not require authentication
      uploadPath = path.join(vaultPath, "public", "media");
      console.log("🌐 [MEDIA UPLOAD] Public upload to:", uploadPath);
    } else {
      // User and project uploads require authentication
      session = await verifySession(cookies);
      if (!session) {
        console.log("❌ [MEDIA UPLOAD] Unauthorized upload attempt");
        return error(401, { message: "Authentication required for user/project uploads" });
      }

      if (level === "user") {
        uploadPath = path.join(vaultPath, session.username, "media");
        console.log("👤 [MEDIA UPLOAD] User upload to:", uploadPath);
      } else if (level === "project") {
        if (!projectId) {
          return error(400, { message: "Project ID required for project-level uploads" });
        }

        // Verify project belongs to user
        const projectData = await db
          .select()
          .from(project)
          .where(and(eq(project.id, projectId), eq(project.userId, session.userId)))
          .limit(1);

        if (projectData.length === 0) {
          return error(404, { message: "Project not found or access denied" });
        }

        // Upload to user's media folder (not project folder)
        uploadPath = path.join(vaultPath, session.username, "media");
        console.log("📁 [MEDIA UPLOAD] Project upload to user media folder:", uploadPath);
      }
    }

    // Create upload directory if it does not exist
    try {
      await fs.mkdir(uploadPath, { recursive: true });
      console.log("📁 [MEDIA UPLOAD] Upload directory created/verified:", uploadPath);
    } catch (dirErr) {
      console.error("❌ [MEDIA UPLOAD] Failed to create upload directory:", dirErr);
      return error(500, { message: "Failed to create upload directory" });
    }

    // Generate unique filename
    const fileExtension = path.extname(file.name);
    const baseName = path.basename(file.name, fileExtension);
    const uniqueId = nanoid(8);
    const uniqueFileName = `${baseName}-${uniqueId}${fileExtension}`;
    const filePath = path.join(uploadPath, uniqueFileName);

    // Save file
    try {
      const arrayBuffer = await file.arrayBuffer();
      const buffer = Buffer.from(arrayBuffer);
      await fs.writeFile(filePath, buffer);
      console.log("✅ [MEDIA UPLOAD] File saved successfully:", filePath);
    } catch (fileErr) {
      console.error("❌ [MEDIA UPLOAD] Failed to save file:", fileErr);
      return error(500, { message: "Failed to save file" });
    }

    // Create material relationship if level is "project"
    if (level === "project" && session) {
      try {
        // Determine file type
        const ext = path.extname(uniqueFileName).toLowerCase();
        let fileType = "unknown";
        if ([".jpg", ".jpeg", ".png", ".gif", ".webp"].includes(ext)) {
          fileType = "image";
        } else if ([".mp4", ".webm", ".avi", ".mov", ".mkv"].includes(ext)) {
          fileType = "video";
        } else if ([".mp3", ".wav", ".ogg", ".aac"].includes(ext)) {
          fileType = "audio";
        }

        // Create material relationship
        const relativePath = path.relative(vaultPath, filePath).replace(/\\/g, '/');
        await db.insert(material).values({
          id: nanoid(),
          projectId,
          relativePath,
          fileName: uniqueFileName,
          fileType,
        });

        console.log("✅ [MEDIA UPLOAD] Material relationship created for project:", projectId);
      } catch (materialErr) {
        console.error("❌ [MEDIA UPLOAD] Failed to create material relationship:", materialErr);
        // Don't fail the upload if material creation fails, but log it
      }
    }

    // Create relative path for client access
    const relativePath = path.relative(vaultPath, filePath).replace(/\\/g, '/');

    const result = {
      success: true,
      file: {
        id: uniqueId,
        name: uniqueFileName,
        originalName: file.name,
        path: relativePath,
        level,
        projectId: projectId || null,
        size: file.size,
        type: file.type,
        uploadedAt: new Date().toISOString(),
      }
    };

    console.log("🎉 [MEDIA UPLOAD] Upload completed successfully");
    return json(result, { status: 201 });

  } catch (err) {
    console.error("❌ [MEDIA UPLOAD] Unexpected error:", err);
    return error(500, { message: "Internal server error" });
  }
}
