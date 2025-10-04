import { json, error } from "@sveltejs/kit";
import { nanoid } from "nanoid";
import { writeFile, mkdir } from "fs/promises";
import { join } from "path";
import { BatchTranslationService } from "$lib/server/batch-translation";
import { verifySession } from "$lib/server/auth";

export async function POST({ request, cookies }) {
  try {
    console.log("🚀 [TRANSLATE API] POST request received");

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log("❌ [TRANSLATE API] Unauthorized - invalid session");
      return json({ error: "Unauthorized" }, { status: 401 });
    }

    const formData = await request.formData();
    const file = formData.get("file") as File;
    const text = formData.get("text") as string;
    const language = formData.get("language") as string;

    console.log("📋 [TRANSLATE API] Request details:", {
      hasFile: !!file,
      fileName: file?.name || "N/A",
      fileSize: file?.size || 0,
      hasText: !!text,
      textLength: text?.length || 0,
      language,
      userId: session.userId,
    });

    if (!file && !text) {
      return error(400, { message: "No file or text provided" });
    }

    if (!language) {
      return error(400, { message: "No language pair specified" });
    }

    // Parse language pair
    const [sourceLang, targetLang] = language.split("-");
    if (!sourceLang || !targetLang) {
      console.log("❌ [TRANSLATE API] Invalid language pair format:", language);
      return error(400, { message: "Invalid language pair format" });
    }

    console.log(
      "🌐 [TRANSLATE API] Language pair:",
      sourceLang,
      "→",
      targetLang,
    );

    // Generate unique task ID
    const taskId = `tid_${nanoid(10)}`;
    console.log("🆔 [TRANSLATE API] Generated task ID:", taskId);

    // Create upload directory if it doesn't exist
    const uploadDir = join(process.cwd(), "uploads");
    await mkdir(uploadDir, { recursive: true });
    console.log("📁 [TRANSLATE API] Upload directory ready:", uploadDir);

    let sourceContent = text;
    let sourceType = "text";
    let sourceFilePath = null;

    // Handle file upload
    if (file) {
      console.log("📄 [TRANSLATE API] Processing file upload:", file.name);
      // Extract file extension, handling potential issues with non-ASCII characters
      const fileExtension = file.name.includes(".")
        ? file.name.split(".").pop()?.toLowerCase()
        : "unknown";
      sourceType = fileExtension || "unknown";

      // Save file to disk using TASK_ID.ORIGINAL_SUFFIX convention
      const originalFileName = file.name;
      const originalFileExtension = fileExtension;
      const savedFileName = `${taskId}.${originalFileExtension}`;
      sourceFilePath = join(uploadDir, savedFileName);

      // Convert file to array buffer and save
      const arrayBuffer = await file.arrayBuffer();
      const buffer = Buffer.from(arrayBuffer);
      await writeFile(sourceFilePath, buffer);
      console.log("💾 [TRANSLATE API] File saved to:", sourceFilePath);

      // Set placeholder content - actual processing will be done by Python service
      sourceContent = `[FILE_UPLOADED] ${file.name}`;
      console.log(
        "📝 [TRANSLATE API] File uploaded, pending Python processing",
      );
    } else {
      console.log(
        "📝 [TRANSLATE API] Processing text input, length:",
        sourceContent.length,
      );
    }

    // Create a single-task batch for backward compatibility
    const batchService = new BatchTranslationService();
    const batchResult = await batchService.createBatch({
      userId: session.userId,
      tasks: [
        {
          sourceLanguage: sourceLang,
          targetLanguage: targetLang,
          sourceType,
          sourceContent,
          sourceFilePath,
          originalFileName,
          originalFileExtension,
        },
      ],
      options: {
        priority: "normal",
        maxInstances: 1,
        timeout: 60000,
      },
    });

    console.log("✅ [TRANSLATE API] Batch created for single task:", {
      batchId: batchResult.batchId,
      taskId: batchResult.taskIds[0],
    });

    // Return the task ID for backward compatibility
    return json({
      success: true,
      taskId: batchResult.taskIds[0],
      batchId: batchResult.batchId,
      message: "Translation started successfully",
    });
  } catch (err) {
    console.error("Translation upload error:", err);
    return error(500, { message: "Internal server error" });
  }
}

async function processTranslation(
  taskId: string,
  content: string,
  sourceLang: string,
  targetLang: string,
) {
  try {
    console.log(
      "🔄 [TRANSLATION PROCESS] Starting translation for task:",
      taskId,
    );
    console.log(
      "📊 [TRANSLATION PROCESS] Content length:",
      content.length,
      "characters",
    );

    // Update task status to processing
    const task = mockTasks.get(taskId);
    if (task) {
      task.status = "processing";
      console.log(
        "⚡ [TRANSLATION PROCESS] Task status updated to: processing",
      );
    }

    // Initialize translation service
    console.log("🤖 [TRANSLATION PROCESS] Initializing translation service...");
    const translationService = new TranslationService();

    // Handle auto-detection
    let actualSourceLang = sourceLang;
    if (sourceLang === "auto") {
      console.log("🔍 [TRANSLATION PROCESS] Auto-detecting language...");
      actualSourceLang = await translationService.detectLanguage(content);
      console.log(
        "🌍 [TRANSLATION PROCESS] Detected language:",
        actualSourceLang,
      );
    }

    console.log(
      "🎯 [TRANSLATION PROCESS] Starting translation:",
      actualSourceLang,
      "→",
      targetLang,
    );

    // Log complete source content
    console.log("📄 [TRANSLATION PROCESS] === COMPLETE SOURCE CONTENT ===");
    console.log(content);
    console.log("📄 [TRANSLATION PROCESS] === END SOURCE CONTENT ===");

    // Perform translation
    const translationResult = await translationService.translate({
      content,
      sourceLanguage: actualSourceLang,
      targetLanguage: targetLang,
    });

    console.log("✅ [TRANSLATION PROCESS] Translation completed successfully");
    console.log(
      "📈 [TRANSLATION PROCESS] Confidence score:",
      translationResult.confidence,
    );
    console.log(
      "📝 [TRANSLATION PROCESS] Translation length:",
      translationResult.translatedContent.length,
      "characters",
    );

    // Log complete translation result
    console.log("🎯 [TRANSLATION PROCESS] === COMPLETE TRANSLATION RESULT ===");
    console.log(translationResult.translatedContent);
    console.log("🎯 [TRANSLATION PROCESS] === END TRANSLATION RESULT ===");

    if (
      translationResult.alternatives &&
      translationResult.alternatives.length > 0
    ) {
      console.log("🔄 [TRANSLATION PROCESS] === ALTERNATIVE TRANSLATIONS ===");
      translationResult.alternatives.forEach((alt, i) => {
        console.log(`🔄 [TRANSLATION PROCESS] Alternative ${i + 1}:`, alt);
      });
      console.log("🔄 [TRANSLATION PROCESS] === END ALTERNATIVES ===");
    }

    // Format the translated content as markdown
    const translatedContent = `# Translation Report

**Source Language:** ${actualSourceLang}
**Target Language:** ${targetLang}
**Confidence:** ${(translationResult.confidence * 100).toFixed(1)}%
**Task ID:** ${taskId}

---

## Translated Content

${translationResult.translatedContent}

---

${
  translationResult.alternatives
    ? `## Alternative Translations

${translationResult.alternatives.map((alt, i) => `${i + 1}. ${alt}`).join("\n\n")}`
    : ""
}

---
*Generated on ${new Date().toISOString()}*`;

    // Save translated content as markdown
    const uploadDir = join(process.cwd(), "uploads");
    const markdownPath = join(uploadDir, `${taskId}.md`);
    await writeFile(markdownPath, translatedContent);
    console.log("💾 [TRANSLATION PROCESS] Translation saved to:", markdownPath);

    // Update task with completed status and file paths
    if (task) {
      task.status = "completed";
      task.markdownPath = markdownPath;
      task.completedAt = new Date();
      console.log("🎉 [TRANSLATION PROCESS] Task marked as completed");
    }
  } catch (err) {
    console.error(
      "❌ [TRANSLATION PROCESS] Translation processing error:",
      err,
    );
    const task = mockTasks.get(taskId);
    if (task) {
      task.status = "failed";
      task.errorMessage = err.message;
      task.completedAt = new Date();
      console.log(
        "💥 [TRANSLATION PROCESS] Task marked as failed:",
        err.message,
      );
    }
  }
}
