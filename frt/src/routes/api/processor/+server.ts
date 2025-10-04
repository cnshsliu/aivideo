import { json, error } from "@sveltejs/kit";
import { continuousBatchProcessor } from "$lib/server/continuous-batch-processor";

export async function POST({ request }) {
  try {
    console.log("🔄 [PROCESSOR API] Manual batch processing trigger");

    // Run the continuous batch processor manually
    await continuousBatchProcessor.processNextBatch();

    return json({
      success: true,
      message: "Batch processor executed successfully",
    });
  } catch (err) {
    console.error("❌ [PROCESSOR API] Batch processor error:", err);
    return error(500, { message: "Internal server error" });
  }
}
