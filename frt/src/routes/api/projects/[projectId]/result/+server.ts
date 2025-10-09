import { error } from "@sveltejs/kit";
import { verifySession } from "$lib/server/auth";
import { db } from "$lib/server/db";
import { project } from "$lib/server/db/schema";
import { eq } from "drizzle-orm";
import fs from "fs/promises";
import fsSync from "fs";
import path from "path";

export async function GET({ params, cookies, url }) {
  try {
    console.log(
      "🎬 [RESULT API] GET request to play result video for progress:",
      params.projectId,
    );

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log("❌ [RESULT API] Unauthorized access attempt");
      return error(401, { message: "Unauthorized" });
    }

    const { projectId } = params;

    // Fetch progress record
    const progressRecord = await db
      .select()
      .from(project)
      .where(eq(project.id, projectId))
      .limit(1);

    if (!progressRecord || progressRecord.length === 0) {
      return error(404, { message: "Progress record not found" });
    }

    const record = progressRecord[0];

    // Check if result file exists
    if (!record.progressResult) {
      return error(404, { message: "Result video not found" });
    }

    try {
      // Check if file exists
      await fs.access(record.progressResult);

      // Check if download parameter is present
      const download = url.searchParams.get('download') === 'true';
      
      // Get filename from path
      const fileName = path.basename(record.progressResult);

      // Create a readable stream
      const stream = fsSync.createReadStream(record.progressResult);

      // Get file stats for content length
      const stats = await fs.stat(record.progressResult);

      // Set headers based on whether it's a download or preview
      const headers: Record<string, string> = {
        'Content-Type': 'video/mp4',
        'Content-Length': stats.size.toString()
      };

      if (download) {
        headers['Content-Disposition'] = `attachment; filename="${fileName}"`;
      }

      // Return video file stream
      return new Response(stream as unknown as BodyInit, {
        headers
      });
    } catch (err) {
      console.error("❌ [RESULT API] Error accessing result file:", err);
      return error(404, { message: "Result video not found" });
    }
  } catch (err) {
    console.error("❌ [RESULT API] Error:", err);
    return error(500, { message: "Internal server error" });
  }
}
