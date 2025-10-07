import { json, error } from "@sveltejs/kit";
import {
  createUser,
  getUserByUsername,
  validateUserCredentials,
  validateUsername,
  validatePassword,
  generateSessionToken,
  createSession,
  setSessionTokenCookie,
} from "$lib/server/auth";

export async function POST(event) {
  const { request, cookies } = event;
  console.log("🔐 [AUTH API] POST request received");

  const formData = await request.formData();
  const username = formData.get("username") as string;
  const password = formData.get("password") as string;

  console.log("📝 [AUTH API] Login attempt for username:", username);

  if (!username || !password) {
    return error(400, { message: "Username and password are required" });
  }

  // Validate input
  const usernameValidation = validateUsername(username);
  if (!usernameValidation.valid) {
    return error(400, usernameValidation.error || "Invalid username");
  }

  const passwordValidation = validatePassword(password);
  if (!passwordValidation.valid) {
    return error(400, passwordValidation.error || "Invalid password");
  }

  // Check if user exists
  const existingUser = await getUserByUsername(username);
  console.log("🔍 [AUTH API] User exists check:", existingUser ? "YES" : "NO");

  if (existingUser) {
    console.log("🔓 [AUTH API] Processing login for existing user");
    // User exists, try to login
    const result = await validateUserCredentials(username, password);

    if (result.error) {
      console.log("❌ [AUTH API] Login failed:", result.error);
      return error(401, result.error);
    }

    if (!result.user) {
      console.log("❌ [AUTH API] Login failed: User not found");
      return error(401, "User not found");
    }

    console.log("✅ [AUTH API] Login successful, creating session");
    try {
      // Create session for existing user
      const sessionToken = generateSessionToken();
      const session = await createSession(sessionToken, result.user.id);
      setSessionTokenCookie(event, sessionToken, session.expiresAt);

      console.log(
        "🎫 [AUTH API] Session created for user:",
        result.user.username,
      );
      return json({
        success: true,
        action: "login",
        user: {
          id: result.user.id,
          username: result.user.username,
        },
        message: "Login successful",
      });
    } catch (err) {
      console.error("❌ [AUTH API] Session creation error:", err);
      return error(500, { message: "Internal server error" });
    }
  } else {
    console.log("👤 [AUTH API] Creating new user account");
    try {
      // User doesn't exist, create new account
      const newUser = await createUser(username, password);
      console.log("✅ [AUTH API] New user created:", newUser.username);

      console.log("🎫 [AUTH API] Creating session for new user");
      // Create session for new user
      const sessionToken = generateSessionToken();
      const session = await createSession(sessionToken, newUser.id);
      setSessionTokenCookie(event, sessionToken, session.expiresAt);

      console.log(
        "🎉 [AUTH API] Registration and login completed successfully",
      );
      return json({
        success: true,
        action: "register",
        user: {
          id: newUser.id,
          username: newUser.username,
        },
        message: "Registration successful",
      });
    } catch (err) {
      console.error("❌ [AUTH API] User creation error:", err);
      return error(500, { message: "Internal server error" });
    }
  }
}
