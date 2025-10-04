import { json, error } from "@sveltejs/kit";
import { mockTasks } from "$lib/server/storage";

export async function GET({ url }) {
  try {
    const userId = url.searchParams.get("userId");
    console.log("📋 [TASKS API] GET request for user ID:", userId);

    if (!userId) {
      console.log("❌ [TASKS API] User ID required but not provided");
      return error(400, { message: "User ID required" });
    }

    // Filter tasks by user ID
    const userTasks = Array.from(mockTasks.values()).filter(
      (task) => task.userId === userId,
    );
    console.log(
      "📊 [TASKS API] Found",
      userTasks.length,
      "tasks for user:",
      userId,
    );
    console.log(
      "📋 [TASKS API] Task statuses:",
      userTasks.map((t) => `${t.taskId}:${t.status}`),
    );

    return json(userTasks);
  } catch (err) {
    console.error("❌ [TASKS API] User tasks retrieval error:", err);
    return error(500, { message: "Internal server error" });
  }
}
