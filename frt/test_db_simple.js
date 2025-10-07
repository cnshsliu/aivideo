// Simple test script to check database access
import postgres from "postgres";

// Test database connection
const client = postgres(
  "postgres://root:mysecretpassword@localhost:5432/local",
  {
    max: 1,
    idle_timeout: 20,
    connect_timeout: 10,
    host: "127.0.0.1",
  },
);

async function testDbAccess() {
  try {
    console.log("Testing database connection...");
    const result = await client`SELECT 1 as test`;
    console.log("Database connection successful:", result);
    
    // Try to fetch a project
    const projects = await client`SELECT * FROM project WHERE id = '_gY_6OFTWzf5GdrmlqC4d'`;
    console.log("Project:", projects[0]);
    
    // Try to insert a progress record
    const progressId = "test-progress-" + Date.now();
    const insertResult = await client`
      INSERT INTO aiv_progress (id, project_id, step, command, result, log) 
      VALUES (${progressId}, ${'_gY_6OFTWzf5GdrmlqC4d'}, ${'preparing'}, ${null}, ${null}, ${null})
      RETURNING *
    `;
    console.log("Successfully inserted progress record:", insertResult[0]);
    
    // Try to update the progress record
    const updateResult = await client`
      UPDATE aiv_progress 
      SET step = ${'running'}, updated_at = ${new Date()} 
      WHERE id = ${progressId}
      RETURNING *
    `;
    console.log("Successfully updated progress record:", updateResult[0]);
    
    // Clean up
    await client`DELETE FROM aiv_progress WHERE id = ${progressId}`;
    console.log("Successfully cleaned up test record");
    
    await client.end();
    process.exit(0);
  } catch (error) {
    console.error("Error:", error);
    await client.end();
    process.exit(1);
  }
}

testDbAccess();
