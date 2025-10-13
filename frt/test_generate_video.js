// Simple test script to call the generate API
import postgres from 'postgres';

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

async function testGenerateVideo() {
  try {
    console.log('Testing database connection...');
    const result = await client`SELECT 1 as test`;
    console.log('Database connection successful:', result);

    // Get the demo user ID
    const users = await client`SELECT * FROM "user" WHERE username = 'demo'`;
    console.log('Demo user:', users[0]);

    // Create a simple session token (in practice, this would be more secure)
    const sessionToken = 'test-session-token-' + Date.now();

    // Create session in database
    const sessionResult = await client`
      INSERT INTO session (id, user_id, expires_at) 
      VALUES (${sessionToken}, ${users[0].id}, ${new Date(Date.now() + 24 * 60 * 60 * 1000)})
      RETURNING *
    `;
    console.log('Created session:', sessionResult[0]);

    // Now make the API call with the session cookie
    console.log('Making API call to generate video...');
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

testGenerateVideo();
