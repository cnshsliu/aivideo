import { json, error } from "@sveltejs/kit";
import { verifySession } from "$lib/server/auth";
import { db } from "$lib/server/db";
import { project } from "$lib/server/db/schema";
import { eq, and } from "drizzle-orm";

export async function GET({ params, cookies }) {
  try {
    console.log(
      "📖 [PROJECT GET API] GET request to fetch project:",
      params.projectId,
    );

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log("❌ [PROJECT GET API] Unauthorized access attempt");
      return error(401, { message: "Unauthorized" });
    }

    const { projectId } = params;

    // Fetch project
    const dbProject = await db
      .select()
      .from(project)
      .where(and(eq(project.id, projectId), eq(project.userId, session.userId)))
      .limit(1);

    if (!dbProject || dbProject.length === 0) {
      return error(404, { message: "Project not found" });
    }

    console.log("✅ [PROJECT GET API] Project fetched:", projectId);

    return json(dbProject[0]);
  } catch (err) {
    console.error("❌ [PROJECT GET API] Project fetch error:", err);
    return error(500, { message: "Internal server error" });
  }
}

export async function PUT({ params, request, cookies }) {
  try {
    console.log(
      "📝 [PROJECT UPDATE API] PUT request to update project:",
      params.projectId,
    );

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log("❌ [PROJECT UPDATE API] Unauthorized access attempt");
      return error(401, { message: "Unauthorized" });
    }

    const { projectId } = params;
    const { title, name, prompt, staticSubtitle } = await request.json();

    if (!title || !name) {
      return error(400, { message: "Title and name are required" });
    }

    // Check if project exists and belongs to user
    const dbProject = await db
      .select()
      .from(project)
      .where(and(eq(project.id, projectId), eq(project.userId, session.userId)))
      .limit(1);

    if (!dbProject || dbProject.length === 0) {
      return error(404, { message: "Project not found" });
    }

    // Check uniqueness of name
    const existingName = await db
      .select()
      .from(project)
      .where(and(eq(project.name, name), eq(project.userId, session.userId)))
      .limit(1);

    if (
      existingName &&
      existingName.length > 0 &&
      existingName[0].id !== projectId
    ) {
      return error(409, { message: "Project name already exists" });
    }

    // Check uniqueness of title
    const existingTitle = await db
      .select()
      .from(project)
      .where(and(eq(project.title, title), eq(project.userId, session.userId)))
      .limit(1);

    if (
      existingTitle &&
      existingTitle.length > 0 &&
      existingTitle[0].id !== projectId
    ) {
      return error(409, { message: "Project title already exists" });
    }

    // Update project
    console.log("prompt=", prompt);
    console.log("staticSubtitle=", staticSubtitle);
    await db
      .update(project)
      .set({ title, name, prompt, staticSubtitle, updatedAt: new Date() })
      .where(
        and(eq(project.id, projectId), eq(project.userId, session.userId)),
      );

    console.log(
      "✅ [PROJECT UPDATE API] Project updated:",
      projectId,
      "name=",
      name,
      "title=",
      title,
    );

    return json({ success: true });
  } catch (err) {
    console.error("❌ [PROJECT UPDATE API] Project update error:", err);
    return error(500, { message: "Internal server error" });
  }
}
