import postgres from 'postgres';
import fs from 'fs/promises';
import path from 'path';

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

async function checkProjectFolder() {
  try {
    console.log('Testing database connection...');
    const result = await client`SELECT 1 as test`;
    console.log('Database connection successful:', result);

    console.log('Fetching project _gY_6OFTWzf5GdrmlqC4d...');
    const projects =
      await client`SELECT * FROM project WHERE id = '_gY_6OFTWzf5GdrmlqC4d'`;
    console.log('Project:', projects[0]);

    // Check if project folder exists
    const vaultPath = './vault';
    const userPath = path.join(vaultPath, 'demo'); // demo is the default user
    const projectPath = path.join(userPath, projects[0].name);

    console.log('Checking if project folder exists:', projectPath);
    try {
      await fs.access(projectPath);
      console.log('Project folder exists!');

      // List contents of project folder
      const files = await fs.readdir(projectPath);
      console.log('Project folder contents:', files);
    } catch (err) {
      console.log('Project folder does not exist:', err.message);
    }

    await client.end();
    process.exit(0);
  } catch (error) {
    console.error('Error:', error);
    await client.end();
    process.exit(1);
  }
}

checkProjectFolder();
