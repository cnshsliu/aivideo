import { json, error } from "@sveltejs/kit";
import { verifySession } from "$lib/server/auth";

export async function GET({ cookies }) {
  try {
    console.log("👤 [USER API] GET request for current user");

    // Verify user session
    const session = await verifySession(cookies);
    if (!session) {
      console.log("❌ [USER API] No active session");
      return error(401, { message: "Unauthorized" });
    }

    console.log("✅ [USER API] User found:", session.username);
    return json({
      id: session.userId,
      username: session.username,
    });
  } catch (err) {
    console.error("❌ [USER API] Error getting current user:", err);
    return error(500, { message: "Internal server error" });
  }
}
