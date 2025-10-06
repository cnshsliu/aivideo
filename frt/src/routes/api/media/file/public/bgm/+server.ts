import { json, error } from "@sveltejs/kit";
import { readdirSync, statSync } from "fs";
import { join } from "path";

// Path to the project's bgm folder
const BGM_PATH = join(process.cwd(), "..", "bgm");

export async function GET() {
  try {
    console.log("🎵 [BGM API] Listing BGM files from:", BGM_PATH);
    
    // Ensure directory exists
    try {
      const files = readdirSync(BGM_PATH);
      console.log("📄 [BGM API] Files found:", files);
      
      const bgmFiles = files
        .filter((file) => {
          const ext = file.split(".").pop()?.toLowerCase() || "";
          return ["mp3", "wav", "ogg", "aac", "flac", "m4a"].includes(ext);
        })
        .map((file) => {
          try {
            const filePath = join(BGM_PATH, file);
            const stats = statSync(filePath);
            
            return {
              name: file,
              size: stats.size,
              modified: stats.mtime.toISOString(),
            };
          } catch (err) {
            console.error(`Error processing file ${file}:`, err);
            return null;
          }
        })
        .filter((item) => item !== null)
        .sort((a, b) => a.name.localeCompare(b.name));

      console.log("✅ [BGM API] Processed BGM files:", bgmFiles.length);
      return json(bgmFiles.map(file => file.name));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      console.log(
        "❌ [BGM API] Directory does not exist or cannot be accessed:",
        message,
      );
      // Directory doesn't exist, return empty array
      return json([]);
    }
  } catch (err) {
    console.error("❌ [BGM API] Error listing BGM files:", err);
    throw error(500, "Failed to list BGM files");
  }
}
