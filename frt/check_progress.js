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

async function checkProgress() {
  try {
    console.log('Testing database connection...');
    const result = await client`SELECT 1 as test`;
    console.log('Database connection successful:', result);

    console.log('Checking aiv_progress table...');
    const progress =
      await client`SELECT * FROM aiv_progress WHERE project_id = '_gY_6OFTWzf5GdrmlqC4d'`;
    console.log('Progress entries:', progress);

    await client.end();
    process.exit(0);
  } catch (error) {
    console.error('Database query failed:', error);
    await client.end();
    process.exit(1);
  }
}

checkProgress();
