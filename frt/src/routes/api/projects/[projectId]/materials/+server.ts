import { json, error, type RequestEvent } from "@sveltejs/kit";
import { db } from "$lib/server/db";
import { material, project } from "$lib/server/db/schema";
import { verifySession } from "$lib/server/auth";
import { nanoid } from "nanoid";
import { eq, and } from "drizzle-orm";
import fs from "fs/promises";
import path from "path";

export async function GET({ params, cookies }: RequestEvent) {
  const projectId = params.projectId;
  if (!projectId) {
    return error(400, { message: "Project ID is required" });
  }

  // Verify user session
  const session = await verifySession(cookies);
  if (!session) {
    return error(401, { message: "Unauthorized" });
  }

  // Verify user owns the project
  const projectData = await db
    .select()
    .from(project)
    .where(and(eq(project.id, projectId), eq(project.userId, session.userId)))
    .limit(1);

  if (projectData.length === 0) {
    return error(404, { message: "Project not found or access denied" });
  }

  // Get materials for the project
  try {
    const materials = await db
      .select()
      .from(material)
      .where(eq(material.projectId, projectId))
      .orderBy(material.createdAt);

    return json(materials);
  } catch (err) {
    console.error("Error fetching project materials:", err);
    return error(500, { message: "Internal server error" });
  }
}

export async function POST({ params, request, cookies }: RequestEvent) {
  const projectId = params.projectId;
  if (!projectId) {
    return error(400, { message: "Project ID is required" });
  }

  // Verify user session
  const session = await verifySession(cookies);
  if (!session) {
    return error(401, { message: "Unauthorized" });
  }

  // Verify user owns the project
  const projectData = await db
    .select()
    .from(project)
    .where(and(eq(project.id, projectId), eq(project.userId, session.userId)))
    .limit(1);

  if (projectData.length === 0) {
    return error(404, { message: "Project not found or access denied" });
  }

  const data = await request.json();
  const { relativePath, fileName, fileType } = data;

  if (!relativePath || !fileName || !fileType) {
    return error(400, {
      message: "Missing required fields: relativePath, fileName, fileType"
    });
  }

  // Validate that the material path is from public or user's own folder
  const vaultPath = process.env.AIV_VAULT_FOLDER || "./vault";
  const fullPath = path.join(vaultPath, relativePath);

  // Check if file exists
  try {
    await fs.access(fullPath);
  } catch {
    return error(400, { message: "Material file does not exist" });
  }

  // Validate path ownership (must be public or user's own folder)
  const pathParts = relativePath.split("/");
  if (pathParts[0] !== "public" && pathParts[0] !== session.username) {
    return error(403, {
      message: "Cannot add materials from other users' folders"
    });
  }

  // Check if material already exists for this project
  const existingMaterial = await db
    .select()
    .from(material)
    .where(and(
      eq(material.projectId, projectId),
      eq(material.relativePath, relativePath)
    ))
    .limit(1);

  if (existingMaterial.length > 0) {
    return error(409, { message: "Material already exists in project" });
  }

  // Create material relationship
  try {
    const newMaterial = await db
      .insert(material)
      .values({
        id: nanoid(),
        projectId,
        relativePath,
        fileName,
        fileType,
      })
      .returning();

    return json(newMaterial[0], { status: 201 });
  } catch (err) {
    console.error("Error adding project material:", err);
    return error(500, { message: "Internal server error" });
  }
}

export async function DELETE({ params, cookies, url }: RequestEvent) {
  try {
    const projectId = params.projectId;
    if (!projectId) {
      return error(400, { message: "Project ID is required" });
    }

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      return error(401, { message: "Unauthorized" });
    }

    // Get material ID from query parameter
    const materialId = url.searchParams.get("materialId");
    if (!materialId) {
      return error(400, { message: "Material ID is required as query parameter" });
    }

    // Check if material exists in project
    const existingMaterial = await db
      .select()
      .from(material)
      .where(and(
        eq(material.id, materialId),
        eq(material.projectId, projectId)
      ))
      .limit(1);

    if (existingMaterial.length === 0) {
      return error(404, { message: "Material not found in project" });
    }

    // Delete material relationship
    await db
      .delete(material)
      .where(and(
        eq(material.id, materialId),
        eq(material.projectId, projectId)
      ));

    return json({ success: true });
  } catch (err) {
    console.error("Error removing project material:", err);
    return error(500, { message: "Internal server error" });
  }
}

