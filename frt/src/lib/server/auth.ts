import type { RequestEvent } from "@sveltejs/kit";
import { sha256 } from "@oslojs/crypto/sha2";
import { encodeBase64url, encodeHexLowerCase } from "@oslojs/encoding";
import { nanoid } from "nanoid";
import { db } from "./db/index.js";
import { user, session as sessionTable } from "./db/schema.js";
import { eq, and, gte } from "drizzle-orm";

const DAY_IN_MS = 1000 * 60 * 60 * 24;

export const sessionCookieName = "auth-session";

export function generateSessionToken() {
  const bytes = crypto.getRandomValues(new Uint8Array(18));
  const token = encodeBase64url(bytes);

  return token;
}

export async function createSession(token: string, userId: string) {
  console.log("🎫 [AUTH] Creating session for user ID:", userId);
  const sessionId = encodeHexLowerCase(sha256(new TextEncoder().encode(token)));

  const session = {
    id: sessionId,
    userId,
    expiresAt: new Date(Date.now() + DAY_IN_MS * 30),
  };

  // Store in database
  await db.insert(sessionTable).values(session);
  console.log("✅ [AUTH] Session created successfully:", sessionId);
  return session;
}

export async function validateSessionToken(token: string) {
  const sessionId = encodeHexLowerCase(sha256(new TextEncoder().encode(token)));

  // Get session from database
  const [session] = await db
    .select()
    .from(sessionTable)
    .where(
      and(
        eq(sessionTable.id, sessionId),
        gte(sessionTable.expiresAt, new Date()),
      ),
    );

  if (!session) {
    console.log("❌ [AUTH] Session validation failed: session not found");
    return { session: null, user: null };
  }

  const [userRecord] = await db
    .select()
    .from(user)
    .where(eq(user.id, session.userId));

  if (!userRecord) {
    console.log(
      "❌ [AUTH] Session validation failed: user not found for session",
    );
    await db.delete(sessionTable).where(eq(sessionTable.id, sessionId));
    return { session: null, user: null };
  }

  const sessionExpired = Date.now() >= session.expiresAt.getTime();

  if (sessionExpired) {
    console.log("❌ [AUTH] Session validation failed: session expired");
    await db.delete(sessionTable).where(eq(sessionTable.id, sessionId));
    return { session: null, user: null };
  }

  const renewSession =
    Date.now() >= session.expiresAt.getTime() - DAY_IN_MS * 15;

  if (renewSession) {
    console.log("🔄 [AUTH] Renewing session:", sessionId);
    await db
      .update(sessionTable)
      .set({ expiresAt: new Date(Date.now() + DAY_IN_MS * 30) })
      .where(eq(sessionTable.id, sessionId));
    session.expiresAt = new Date(Date.now() + DAY_IN_MS * 30);
  }

  console.log(
    "✅ [AUTH] Session validated successfully for user:",
    userRecord.username,
  );
  return {
    session,
    user: { id: userRecord.id, username: userRecord.username },
  };
}

export type SessionValidationResult = Awaited<
  ReturnType<typeof validateSessionToken>
>;

export async function invalidateSession(sessionId: string) {
  console.log("🗑️ [AUTH] Invalidating session:", sessionId);
  await db.delete(sessionTable).where(eq(sessionTable.id, sessionId));
  console.log("✅ [AUTH] Session invalidated");
}

export function setSessionTokenCookie(
  event: RequestEvent,
  token: string,
  expiresAt: Date,
) {
  event.cookies.set(sessionCookieName, token, {
    expires: expiresAt,
    path: "/",
  });
}

export function deleteSessionTokenCookie(event: RequestEvent) {
  event.cookies.delete(sessionCookieName, { path: "/" });
}

// Password hashing with SHA-256 (simplified for demo)
export async function hashPassword(password: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(password + "salt_for_translation_service");
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function verifyPassword(
  password: string,
  hash: string,
): Promise<boolean> {
  const hashedPassword = await hashPassword(password);
  return hashedPassword === hash;
}

// Add a default user for testing
async function ensureDemoUser() {
  const [existingUser] = await db
    .select()
    .from(user)
    .where(eq(user.username, "demo"));

  if (!existingUser) {
    console.log("👤 [AUTH] Creating default demo user...");
    const defaultUser = {
      id: "user_default123",
      username: "demo",
      passwordHash: await hashPassword("demo123"),
      balance: "10.00",
    };
    await db.insert(user).values(defaultUser);
    console.log("✅ [AUTH] Default demo user created successfully");
  }
}

// Initialize demo user
ensureDemoUser().catch(console.error);

// User management functions
export async function createUser(username: string, password: string) {
  console.log("👤 [AUTH] Creating new user:", username);
  const userId = nanoid();
  const passwordHash = await hashPassword(password);

  const newUser = {
    id: userId,
    username,
    passwordHash,
    balance: "0.00",
  };

  // Store in database
  await db.insert(user).values(newUser);
  console.log("✅ [AUTH] User created successfully:", username, "ID:", userId);
  return newUser;
}

export async function getUserByUsername(username: string) {
  const [userRecord] = await db
    .select()
    .from(user)
    .where(eq(user.username, username));
  return userRecord || null;
}

export async function getUserById(userId: string) {
  const [userRecord] = await db.select().from(user).where(eq(user.id, userId));
  return userRecord || null;
}

export async function validateUserCredentials(
  username: string,
  password: string,
) {
  const user = await getUserByUsername(username);

  if (!user) {
    return { user: null, error: "User not found" };
  }

  const isValidPassword = await verifyPassword(password, user.passwordHash);

  if (!isValidPassword) {
    return { user: null, error: "Invalid password" };
  }

  return { user, error: null };
}

// Input validation
export function validateUsername(username: string): {
  valid: boolean;
  error?: string;
} {
  if (typeof username !== "string") {
    return { valid: false, error: "Username must be a string" };
  }

  if (username.length < 3) {
    return {
      valid: false,
      error: "Username must be at least 3 characters long",
    };
  }

  if (username.length > 31) {
    return {
      valid: false,
      error: "Username must be less than 32 characters long",
    };
  }

  if (!/^[a-z0-9_-]+$/.test(username)) {
    return {
      valid: false,
      error:
        "Username can only contain lowercase letters, numbers, underscores, and hyphens",
    };
  }

  return { valid: true };
}

export function validatePassword(password: string): {
  valid: boolean;
  error?: string;
} {
  if (typeof password !== "string") {
    return { valid: false, error: "Password must be a string" };
  }

  if (password.length < 6) {
    return {
      valid: false,
      error: "Password must be at least 6 characters long",
    };
  }

  if (password.length > 255) {
    return {
      valid: false,
      error: "Password must be less than 256 characters long",
    };
  }

  return { valid: true };
}

// Session verification for API endpoints
export async function verifySession(cookies: any) {
  const sessionToken = cookies.get(sessionCookieName);

  if (!sessionToken) {
    return null;
  }

  const { session, user } = await validateSessionToken(sessionToken);

  if (!session || !user) {
    return null;
  }

  return { userId: user.id, username: user.username };
}
