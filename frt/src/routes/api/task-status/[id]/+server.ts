import { json, error } from "@sveltejs/kit";
import { db } from "$lib/server/db/index.js";
import { translationTask } from "$lib/server/db/schema.js";
import { eq, and, isNull } from "drizzle-orm";
import { verifySession } from "$lib/server/auth";

export async function GET({ params, cookies }) {
  try {
    console.log("📊 [TASK STATUS API] GET request for task ID:", params.id);

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log("❌ [TASK STATUS API] Unauthorized - invalid session");
      return json({ error: "Unauthorized" }, { status: 401 });
    }

    const { id } = params;

    // Get task details
    const task = await db
      .select()
      .from(translationTask)
      .where(
        and(
          eq(translationTask.taskId, id),
          eq(translationTask.userId, session.userId),
        ),
      )
      .limit(1);

    if (!task || task.length === 0) {
      console.log("❌ [TASK STATUS API] Task not found:", id);
      return error(404, { message: "Task not found" });
    }

    const taskData = task[0];
    console.log("✅ [TASK STATUS API] Task found:", {
      taskId: taskData.taskId,
      status: taskData.status,
      sourceType: taskData.sourceType,
      hasTranslatedFile: !!taskData.docxPath,
      createdAt: taskData.createdAt,
      completedAt: taskData.completedAt,
    });

    // Determine if the task is ready for download
    const isReadyForDownload =
      taskData.status === "completed" && taskData.docxPath;
    const isProcessing = [
      "pending",
      "processing",
      "pending_python_processing",
    ].includes(taskData.status);
    const isFailed = taskData.status === "failed";

    // Construct response
    const response = {
      taskId: taskData.taskId,
      status: taskData.status,
      sourceType: taskData.sourceType,
      sourceLanguage: taskData.sourceLanguage,
      targetLanguage: taskData.targetLanguage,
      createdAt: taskData.createdAt,
      startedAt: taskData.startedAt,
      completedAt: taskData.completedAt,
      errorMessage: taskData.errorMessage,
      isReadyForDownload,
      isProcessing,
      isFailed,
      progress: calculateProgress(taskData.status),
      estimatedTimeRemaining: estimateTimeRemaining(taskData),
    };

    console.log("📋 [TASK STATUS API] Response:", {
      status: response.status,
      isReadyForDownload: response.isReadyForDownload,
      isProcessing: response.isProcessing,
      progress: response.progress,
    });

    return json(response);
  } catch (err) {
    console.error("❌ [TASK STATUS API] Error:", err);
    return error(500, { message: "Internal server error" });
  }
}

function calculateProgress(status: string): number {
  // Calculate progress percentage based on task status.
  switch (status) {
    case "pending":
      return 0;
    case "processing":
      return 25;
    case "pending_python_processing":
      return 50;
    case "completed":
      return 100;
    case "failed":
      return 0;
    default:
      return 0;
  }
}

function estimateTimeRemaining(taskData: any): string | null {
  // Estimate remaining time based on task status and file type.
  if (taskData.status === "completed") {
    return null;
  }

  if (taskData.status === "failed") {
    return null;
  }

  if (taskData.status === "pending") {
    return "Starting...";
  }

  if (taskData.status === "processing") {
    return "Processing text content...";
  }

  if (taskData.status === "pending_python_processing") {
    if (taskData.sourceType === "docx") {
      return "Translating document (2-5 minutes)";
    } else {
      return "Processing file (1-2 minutes)";
    }
  }

  return "Processing...";
}
