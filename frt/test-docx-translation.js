import fs from "fs";
import path from "path";
import FormData from "form-data";
import fetch from "node-fetch";

// Read the test DOCX file
const filePath = path.join(process.cwd(), "test.docx");
const fileBuffer = fs.readFileSync(filePath);

// Create form data
const form = new FormData();
form.append("file", fileBuffer, {
  filename: "test.docx",
  contentType:
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
});
form.append("language", "en-zh");

// Send the request
fetch("http://localhost:5173/api/translate", {
  method: "POST",
  body: form,
  headers: {
    ...form.getHeaders(),
  },
})
  .then((response) => response.json())
  .then((data) => {
    console.log("Translation request response:", data);
  })
  .catch((error) => {
    console.error("Error:", error);
  });
