// Test script to call the generate API with a valid session
import postgres from 'postgres';
import { createSession, generateSessionToken } from './src/lib/server/auth.ts';

// Test database connection
const client = postgres(
  'postgres://root:mysecretpassword@localhost:5432/local',
  {
    max: 1,
    idle_timeout: 20,
    connect_timeout: 10,
    host: '127.0.0.1'
  }
);

async function testGenerateWithSession() {
  try {
    console.log('Testing database connection...');
    const result = await client`SELECT 1 as test`;
    console.log('Database connection successful:', result);

    // Create a session for the demo user
    const sessionToken = generateSessionToken();
    console.log('Generated session token:', sessionToken);

    // Get the demo user ID
    const users = await client`SELECT * FROM "user" WHERE username = 'demo'`;
    console.log('Demo user:', users[0]);

    // Create session in database
    const session = await createSession(sessionToken, users[0].id);
    console.log('Created session:', session);

    // Now make the API call with the session cookie
    console.log('Making API call with session...');
    const response = await fetch(
      'http://localhost:5173/api/projects/_gY_6OFTWzf5GdrmlqC4d/generate',
      {
        method: 'POST',
        headers: {
          Cookie: `auth-session=${sessionToken}`
        }
      }
    );

    console.log('Response status:', response.status);
    const responseBody = await response.text();
    console.log('Response body:', responseBody);

    await client.end();
    process.exit(0);
  } catch (error) {
    console.error('Error:', error);
    await client.end();
    process.exit(1);
  }
}

testGenerateWithSession();
