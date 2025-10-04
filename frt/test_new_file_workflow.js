#!/usr/bin/env node

/**
 * Test script for the new file handling workflow
 * This script tests the complete flow:
 * 1. Upload a DOCX file
 * 2. Check that it's saved as TASK_ID.ORIGINAL_SUFFIX
 * 3. Monitor task status
 * 4. Check that Python service outputs as TASK_ID_translated.ORIGINAL_SUFFIX
 * 5. Download and verify filename restoration
 */

import fs from "fs";
import path from "path";
import FormData from "form-data";
import fetch from "node-fetch";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const BASE_URL = "http://localhost:5174";

async function testWorkflow() {
  console.log("🚀 Starting new file handling workflow test...");

  try {
    // Step 1: Create a test DOCX file
    console.log("📄 Creating test DOCX file...");
    const testDocxContent = Buffer.from(
      "This is a test DOCX file content",
      "utf-8",
    );
    const testDocxPath = path.join(__dirname, "test_upload.docx");
    fs.writeFileSync(testDocxPath, testDocxContent);

    // Step 2: Upload the file
    console.log("📤 Uploading file...");
    const formData = new FormData();
    formData.append(
      "file",
      fs.createReadStream(testDocxPath),
      "test_upload.docx",
    );
    formData.append("language", "en-zh");

    const uploadResponse = await fetch(`${BASE_URL}/api/translate`, {
      method: "POST",
      body: formData,
    });

    if (!uploadResponse.ok) {
      throw new Error(`Upload failed: ${uploadResponse.statusText}`);
    }

    const uploadResult = await uploadResponse.json();
    console.log("✅ Upload successful:", uploadResult);

    const taskId = uploadResult.taskId;
    console.log("🆔 Task ID:", taskId);

    // Step 3: Check that file is saved with correct naming
    console.log("🔍 Checking file storage...");
    const uploadsDir = path.join(__dirname, "uploads");
    const expectedFileName = `${taskId}.docx`;
    const expectedFilePath = path.join(uploadsDir, expectedFileName);

    if (fs.existsSync(expectedFilePath)) {
      console.log(
        "✅ File saved with correct naming convention:",
        expectedFileName,
      );
    } else {
      console.log("❌ File not found at expected location:", expectedFilePath);
    }

    // Step 4: Monitor task status
    console.log("⏳ Monitoring task status...");
    let taskStatus = "pending";
    let attempts = 0;
    const maxAttempts = 30; // 5 minutes max wait

    while (
      taskStatus !== "completed" &&
      taskStatus !== "failed" &&
      attempts < maxAttempts
    ) {
      await new Promise((resolve) => setTimeout(resolve, 10000)); // Wait 10 seconds

      const statusResponse = await fetch(
        `${BASE_URL}/api/task-status/${taskId}`,
      );
      if (statusResponse.ok) {
        const statusData = await statusResponse.json();
        taskStatus = statusData.status;
        console.log(`📊 Status check ${attempts + 1}: ${taskStatus}`);
      }

      attempts++;
    }

    if (taskStatus === "completed") {
      console.log("✅ Task completed successfully");

      // Step 5: Check for translated file
      const translatedFileName = `${taskId}_translated.docx`;
      const translatedFilePath = path.join(uploadsDir, translatedFileName);

      if (fs.existsSync(translatedFilePath)) {
        console.log(
          "✅ Translated file found with correct naming convention:",
          translatedFileName,
        );
      } else {
        console.log("❌ Translated file not found:", translatedFilePath);
      }

      // Step 6: Test download with filename restoration
      console.log("📥 Testing download...");
      const downloadResponse = await fetch(
        `${BASE_URL}/api/download/${taskId}?format=docx`,
      );

      if (downloadResponse.ok) {
        const contentDisposition = downloadResponse.headers.get(
          "content-disposition",
        );
        console.log("📋 Content-Disposition header:", contentDisposition);

        if (
          contentDisposition &&
          contentDisposition.includes("translated_test_upload.docx")
        ) {
          console.log("✅ Original filename restored with translation prefix");
        } else {
          console.log("⚠️ Filename restoration may not be working correctly");
        }

        // Save downloaded file for verification
        const downloadBuffer = await downloadResponse.buffer();
        const downloadPath = path.join(__dirname, "downloaded_file.docx");
        fs.writeFileSync(downloadPath, downloadBuffer);
        console.log("💾 Downloaded file saved for verification");
      } else {
        console.log("❌ Download failed:", downloadResponse.statusText);
      }
    } else {
      console.log("❌ Task failed or timed out. Final status:", taskStatus);
    }

    // Cleanup
    console.log("🧹 Cleaning up test files...");
    if (fs.existsSync(testDocxPath)) fs.unlinkSync(testDocxPath);

    console.log("🎉 Workflow test completed!");
  } catch (error) {
    console.error("❌ Test failed:", error);
  }
}

// Run the test
testWorkflow();
