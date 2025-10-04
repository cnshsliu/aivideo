import { json, error } from "@sveltejs/kit";
import { db } from "$lib/server/db";
import { project } from "$lib/server/db/schema";
import { verifySession } from "$lib/server/auth";
import { nanoid } from "nanoid";
import fs from "fs/promises";
import path from "path";
import { eq, desc } from "drizzle-orm";

// Import project schema - we'll need to create this
// For now, let's assume we have a project table
// import { project } from '$lib/server/db/schema';

export async function GET({ cookies }) {
  try {
    console.log("📋 [PROJECTS API] GET request for user projects");
    console.log("🍪 [PROJECTS API] Cookies:", cookies.getAll().map(c => c.name));

    // Verify user session
    const session = await verifySession(cookies);
    console.log("🔐 [PROJECTS API] Session verification result:", session ? "VALID" : "INVALID");

    if (!session) {
      console.log("❌ [PROJECTS API] Unauthorized access attempt");
      return error(401, { message: "Unauthorized" });
    }

    const userId = session.userId;
    console.log("📋 [PROJECTS API] Fetching projects for user:", userId);

    // Get user's projects from database
    const projects = await db
      .select()
      .from(project)
      .where(eq(project.userId, userId))
      .orderBy(desc(project.createdAt));

    console.log(
      "📊 [PROJECTS API] Found",
      projects.length,
      "projects for user:",
      userId,
    );

    return json(projects);
  } catch (err) {
    console.error("❌ [PROJECTS API] User projects retrieval error:", err);
    return error(500, { message: "Internal server error" });
  }
}

export async function POST({ request, cookies }) {
  try {
    console.log("➕ [PROJECTS API] POST request to create new project");

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log("❌ [PROJECTS API] Unauthorized project creation attempt");
      return error(401, { message: "Unauthorized" });
    }

    const userId = session.userId;
    console.log("📋 [PROJECTS API] Creating project for user:", userId);

    const data = await request.json();
    console.log("📋 [PROJECTS API] Project data:", data);

    // Validate required fields
    const { name, title } = data;

    if (!name || !title) {
      console.log("❌ [PROJECTS API] Missing required fields");
      return error(400, {
        message: "Missing required fields: name and title",
      });
    }

    // Generate project ID
    const projectId = nanoid();

    // Create project in database
    const newProject = await db
      .insert(project)
      .values({
        id: projectId,
        name: name,
        title: title,
        userId,
        prompt: null,
        staticSubtitle: null,
      })
      .returning();

    if (!newProject || newProject.length === 0) {
      console.error("❌ [PROJECTS API] Failed to create project in database");
      return error(500, { message: "Failed to create project" });
    }

    // Create project folder structure
    const vaultPath = process.env.AIV_VAULT_FOLDER || "./vault";
    const userPath = path.join(vaultPath, session.username);
    const projectPath = path.join(userPath, name);

    try {
      // Create project directory structure
      await fs.mkdir(path.join(projectPath, "media"), { recursive: true });
      await fs.mkdir(path.join(projectPath, "output"), { recursive: true });
      await fs.mkdir(path.join(projectPath, "prompt"), { recursive: true });
      await fs.mkdir(path.join(projectPath, "subtitle"), { recursive: true });

      // Create initial prompt.md file
      const promptFilePath = path.join(projectPath, "prompt", "prompt.md");
      await fs.writeFile(
        promptFilePath,
        "Enter your video generation prompt here...\n",
      );

      console.log(
        "✅ [PROJECTS API] Project folder structure created:",
        projectPath,
      );
    } catch (fsErr) {
      console.error(
        "❌ [PROJECTS API] Failed to create project folders:",
        fsErr,
      );
      return error(500, { message: "Failed to create project folders" });
    }

    console.log("✅ [PROJECTS API] Project created:", projectId);

    return json(newProject, { status: 201 });
  } catch (err) {
    console.error("❌ [PROJECTS API] Project creation error:", err);
    return error(500, { message: "Internal server error" });
  }
}
