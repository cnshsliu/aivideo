import { db } from './src/lib/server/db/index.js';
import { material } from './src/lib/server/db/schema.js';
import { sql } from 'drizzle-orm';

async function fillAliases() {
  try {
    await db
      .update(material)
      .set({ alias: sql`file_name` })
      .where(sql`${material.alias} IS NULL OR ${material.alias} = ''`);
    console.log('Aliases filled for existing materials');
  } catch (err) {
    console.error('Error filling aliases:', err);
  } finally {
    process.exit(0);
  }
}

fillAliases();
