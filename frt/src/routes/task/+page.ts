import type { PageData } from "./$types";
import { error } from "@sveltejs/kit";

export const load = async ({ url }: { url: URL }): Promise<PageData> => {
  // Get the task ID from URL query parameters
  const tid = url.searchParams.get("tid");

  if (!tid) {
    throw error(400, {
      message: "Task ID is required",
    });
  }

  console.log("📋 [TASK PAGE LOAD] Loading task data for TID:", tid);

  return {
    tid: tid,
  };
};
