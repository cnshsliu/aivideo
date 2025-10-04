import { json, error } from "@sveltejs/kit";
import { db } from "$lib/server/db/index.js";
import { translationTask } from "$lib/server/db/schema.js";
import { eq, and } from "drizzle-orm";
import { verifySession } from "$lib/server/auth";
import { readFile } from "fs/promises";
import { join } from "path";

export async function GET({ params, cookies }) {
  try {
    console.log("👁️ [PREVIEW API] GET request for task ID:", params.id);

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log("❌ [PREVIEW API] Unauthorized - invalid session");
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
      console.log("❌ [PREVIEW API] Task not found:", id);
      return error(404, { message: "Task not found" });
    }

    const taskData = task[0];
    console.log("✅ [PREVIEW API] Task found:", {
      taskId: taskData.taskId,
      status: taskData.status,
      sourceType: taskData.sourceType,
      hasTranslatedFile: !!taskData.docxPath,
      hasSourceFile: !!taskData.sourceFilePath,
    });

    // Check if task is completed and has previewable content
    if (taskData.status !== "completed") {
      return json(
        {
          error: "Task not completed",
          status: taskData.status,
          message: "Preview is only available for completed tasks",
        },
        { status: 400 },
      );
    }

    let previewContent = "";
    let previewType = "text";
    let fileName = "";

    // Try to get content from different sources
    if (taskData.docxPath) {
      // Extract text from translated DOCX file
      try {
        const { extractRawText } = await import("mammoth");
        const result = await extractRawText({ path: taskData.docxPath });
        previewContent = result.value;
        previewType = "translated_docx";
        fileName = `${id}_translated.docx`;
        console.log(
          "📄 [PREVIEW API] Extracted text from translated DOCX:",
          previewContent.length,
          "characters",
        );
      } catch (err) {
        console.error(
          "❌ [PREVIEW API] Failed to extract text from translated DOCX:",
          err,
        );
        previewContent = "Could not extract text from translated document.";
      }
    } else if (taskData.sourceFilePath && taskData.sourceType === "docx") {
      // Extract text from source DOCX file
      try {
        const { extractRawText } = await import("mammoth");
        const result = await extractRawText({ path: taskData.sourceFilePath });
        previewContent = result.value;
        previewType = "source_docx";
        fileName = `${id}_original.docx`;
        console.log(
          "📄 [PREVIEW API] Extracted text from source DOCX:",
          previewContent.length,
          "characters",
        );
      } catch (err) {
        console.error(
          "❌ [PREVIEW API] Failed to extract text from source DOCX:",
          err,
        );
        previewContent = "Could not extract text from source document.";
      }
    } else if (taskData.sourceContent) {
      // Use stored content
      previewContent = taskData.sourceContent;
      previewType = "stored_text";
      console.log(
        "📝 [PREVIEW API] Using stored content:",
        previewContent.length,
        "characters",
      );
    } else {
      return json(
        {
          error: "No previewable content available",
          status: taskData.status,
          message: "This task does not have content available for preview",
        },
        { status: 404 },
      );
    }

    // Clean and format the preview content
    const formattedPreview = formatPreviewContent(previewContent);

    // Construct response
    const response = {
      taskId: taskData.taskId,
      status: taskData.status,
      sourceType: taskData.sourceType,
      sourceLanguage: taskData.sourceLanguage,
      targetLanguage: taskData.targetLanguage,
      previewType,
      fileName,
      content: formattedPreview,
      metadata: {
        characterCount: previewContent.length,
        wordCount: previewContent.split(/\s+/).length,
        lineCount: previewContent.split("\n").length,
        createdAt: taskData.createdAt,
        completedAt: taskData.completedAt,
      },
      downloadUrls: {
        docx: `/api/download/${id}?format=docx`,
        markdown: `/api/download/${id}?format=markdown`,
      },
    };

    console.log("👁️ [PREVIEW API] Preview generated:", {
      previewType: response.previewType,
      characterCount: response.metadata.characterCount,
      wordCount: response.metadata.wordCount,
    });

    return json(response);
  } catch (err) {
    console.error("❌ [PREVIEW API] Error:", err);
    return error(500, { message: "Internal server error" });
  }
}

function formatPreviewContent(content: string): any {
  // Format content for web preview with basic structure analysis.
  // Split into lines and analyze structure
  const lines = content.split("\n");
  const paragraphs = lines.filter((line) => line.trim().length > 0);
  const sentences = content.split(/[.!?]+/).filter((s) => s.trim().length > 0);

  // Extract first few lines for preview
  const previewLines = lines.slice(0, 10).join("\n");

  // Detect if content might be translated (basic heuristics)
  const mightBeTranslated =
    /[\u4e00-\u9fff\u0400-\u04ff\u3040-\u309f\u30a0-\u30ff]/.test(content);

  return {
    fullText: content,
    preview: previewLines,
    structure: {
      totalLines: lines.length,
      paragraphs: paragraphs.length,
      sentences: sentences.length,
      hasHeadings: lines.some((line) => /^#{1,6}\s/.test(line)),
      hasLists: lines.some(
        (line) => /^[\*\-\+]\s/.test(line) || /^\d+\.\s/.test(line),
      ),
      mightBeTranslated,
    },
    languageHint: mightBeTranslated
      ? "Content may contain non-Latin characters"
      : "Content appears to be Latin-based",
  };
}
