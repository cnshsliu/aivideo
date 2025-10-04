import fs from "fs";
import path from "path";

// Function to test file upload
async function testDocxUpload() {
  try {
    // Read the test DOCX file
    const filePath = path.join(process.cwd(), "test_document.docx");
    const fileBuffer = fs.readFileSync(filePath);

    // Create a FormData-like object using fetch
    const formData = new FormData();
    formData.append("file", new Blob([fileBuffer]), "test_document.docx");
    formData.append("language", "en-zh");

    // Send the request
    const response = await fetch("http://localhost:5173/api/translate", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    console.log("Translation request response:", data);

    if (data.taskId) {
      console.log("Task created successfully with ID:", data.taskId);

      // Poll for task completion
      const pollForCompletion = async () => {
        const taskResponse = await fetch(
          `http://localhost:5173/api/task/${data.taskId}`,
        );
        const taskData = await taskResponse.json();
        console.log("Task status:", taskData);

        if (taskData.status === "completed") {
          console.log("Task completed!");
          // Try to download the translated file
          const downloadResponse = await fetch(
            `http://localhost:5173/api/download/${data.taskId}?format=docx`,
          );
          if (downloadResponse.ok) {
            console.log("Translated DOCX file is ready for download");
          } else {
            console.log("Error downloading file:", downloadResponse.status);
          }
        } else if (taskData.status === "failed") {
          console.log("Task failed:", taskData.errorMessage);
        } else {
          console.log("Task still processing, checking again in 2 seconds...");
          setTimeout(pollForCompletion, 2000);
        }
      };

      // Start polling
      setTimeout(pollForCompletion, 2000);
    }
  } catch (error) {
    console.error("Error:", error);
  }
}

// Run the test
testDocxUpload();
