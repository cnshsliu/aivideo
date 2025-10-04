import { json, error } from "@sveltejs/kit";
import {
  validateSessionToken,
  invalidateSession,
  deleteSessionTokenCookie,
} from "$lib/server/auth";

export async function POST({ request, cookies }) {
  try {
    console.log("🚪 [LOGOUT API] POST request received");

    const sessionToken = cookies.get("auth-session");
    console.log(
      "🍪 [LOGOUT API] Session token found:",
      sessionToken ? "YES" : "NO",
    );

    if (!sessionToken) {
      console.log("❌ [LOGOUT API] No active session found");
      return error(400, { message: "No active session" });
    }

    const { session } = await validateSessionToken(sessionToken);
    console.log(
      "🔍 [LOGOUT API] Session validation result:",
      session ? "VALID" : "INVALID",
    );

    if (session) {
      await invalidateSession(session.id);
      console.log("🗑️ [LOGOUT API] Session invalidated:", session.id);
    }

    deleteSessionTokenCookie({ cookies });
    console.log("🍪 [LOGOUT API] Session cookie deleted");

    console.log("✅ [LOGOUT API] Logout completed successfully");
    return json({
      success: true,
      message: "Logout successful",
    });
  } catch (err) {
    console.error("❌ [LOGOUT API] Logout error:", err);
    return error(500, { message: "Internal server error" });
  }
}
