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

async function testConnection() {
  try {
    console.log('Testing database connection...');
    const result = await client`SELECT 1 as test`;
    console.log('Database connection successful:', result);
    await client.end();
    process.exit(0);
  } catch (error) {
    console.error('Database connection failed:', error);
    await client.end();
    process.exit(1);
  }
}

testConnection();
