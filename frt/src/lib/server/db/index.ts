import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema";
import { env } from "$env/dynamic/private";

console.log("🔍 [DB] DATABASE_URL:", env.DATABASE_URL);

if (!env.DATABASE_URL) throw new Error("DATABASE_URL is not set");

// More robust connection configuration
const client = postgres(env.DATABASE_URL, {
  onnotice: (notice) => {
    console.log("🔍 [DB] Notice:", notice);
  },
  // Add connection retry options
  max: 20,
  idle_timeout: 20,
  connect_timeout: 10,
  // Force IPv4 to avoid ECONNREFUSED on IPv6
  host: "127.0.0.1",
});

export const db = drizzle(client, { schema });
