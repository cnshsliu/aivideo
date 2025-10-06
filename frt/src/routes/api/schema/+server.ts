import { json, error } from "@sveltejs/kit";
import { db } from "$lib/server/db";
import { sql } from "drizzle-orm";
import type { RequestHandler } from "./$types";

// Define the structure for schema modification requests
interface SchemaModificationRequest {
  action: "addColumn" | "dropColumn" | "modifyColumn" | "addConstraint" | "dropConstraint";
  table: string;
  column?: string;
  type?: string;
  constraintName?: string;
  constraintType?: "primaryKey" | "unique" | "check" | "notNull";
  checkExpression?: string;
  newColumnName?: string;
  newName?: string;
  defaultValue?: any;
  isNullable?: boolean;
}

/**
 * Schema Modification API
 * Allows dynamic modification of PostgreSQL table structure
 * 
 * POST /api/schema
 * 
 * Request body:
 * {
 *   "action": "addColumn" | "dropColumn" | "modifyColumn" | "addConstraint" | "dropConstraint",
 *   "table": "table_name",
 *   "column": "column_name",
 *   "type": "data_type",
 *   "constraintName": "constraint_name",
 *   "constraintType": "primaryKey" | "unique" | "check" | "notNull",
 *   "checkExpression": "expression_for_check_constraints",
 *   "newColumnName": "new_column_name",
 *   "newName": "new_name_for_column_or_constraint",
 *   "defaultValue": "default_value",
 *   "isNullable": boolean
 * }
 * 
 * Response:
 * {
 *   "success": boolean,
 *   "message": "Description of the operation result",
 *   "sql": "The SQL statement that was executed"
 * }
 */

export const POST: RequestHandler = async ({ request }) => {
  try {
    // Parse the request body
    const body: SchemaModificationRequest = await request.json();
    
    // Validate the request
    if (!body.action || !body.table) {
      throw error(400, "Action and table are required");
    }
    
    // Generate the SQL statement based on the action
    let sqlStatement = "";
    
    switch (body.action) {
      case "addColumn":
        if (!body.column || !body.type) {
          throw error(400, "Column name and type are required for addColumn action");
        }
        sqlStatement = `ALTER TABLE "${body.table}" ADD COLUMN "${body.column}" ${body.type}`;
        if (body.defaultValue !== undefined) {
          sqlStatement += ` DEFAULT ${typeof body.defaultValue === 'string' ? `'${body.defaultValue}'` : body.defaultValue}`;
        }
        if (body.isNullable === false) {
          sqlStatement += " NOT NULL";
        }
        break;
        
      case "dropColumn":
        if (!body.column) {
          throw error(400, "Column name is required for dropColumn action");
        }
        sqlStatement = `ALTER TABLE "${body.table}" DROP COLUMN "${body.column}"`;
        break;
        
      case "modifyColumn":
        if (!body.column || !body.type) {
          throw error(400, "Column name and type are required for modifyColumn action");
        }
        sqlStatement = `ALTER TABLE "${body.table}" ALTER COLUMN "${body.column}" TYPE ${body.type}`;
        if (body.newName) {
          sqlStatement += `; ALTER TABLE "${body.table}" RENAME COLUMN "${body.column}" TO "${body.newName}"`;
        }
        break;
        
      case "addConstraint":
        if (!body.constraintName || !body.constraintType) {
          throw error(400, "Constraint name and type are required for addConstraint action");
        }
        switch (body.constraintType) {
          case "primaryKey":
            if (!body.column) {
              throw error(400, "Column name is required for primary key constraint");
            }
            sqlStatement = `ALTER TABLE "${body.table}" ADD CONSTRAINT "${body.constraintName}" PRIMARY KEY ("${body.column}")`;
            break;
          case "unique":
            if (!body.column) {
              throw error(400, "Column name is required for unique constraint");
            }
            sqlStatement = `ALTER TABLE "${body.table}" ADD CONSTRAINT "${body.constraintName}" UNIQUE ("${body.column}")`;
            break;
          case "check":
            if (!body.checkExpression) {
              throw error(400, "Check expression is required for check constraint");
            }
            sqlStatement = `ALTER TABLE "${body.table}" ADD CONSTRAINT "${body.constraintName}" CHECK (${body.checkExpression})`;
            break;
          case "notNull":
            if (!body.column) {
              throw error(400, "Column name is required for not null constraint");
            }
            sqlStatement = `ALTER TABLE "${body.table}" ALTER COLUMN "${body.column}" SET NOT NULL`;
            break;
          default:
            throw error(400, "Invalid constraint type");
        }
        break;
        
      case "dropConstraint":
        if (!body.constraintName) {
          throw error(400, "Constraint name is required for dropConstraint action");
        }
        sqlStatement = `ALTER TABLE "${body.table}" DROP CONSTRAINT "${body.constraintName}"`;
        break;
        
      default:
        throw error(400, "Invalid action");
    }
    
    // Execute the SQL statement
    console.log(`[SCHEMA API] Executing SQL: ${sqlStatement}`);
    await db.execute(sql`${sql.raw(sqlStatement)}`);
    
    // Return success response
    return json({
      success: true,
      message: `Successfully executed ${body.action} on table ${body.table}`,
      sql: sqlStatement
    });
  } catch (err: any) {
    console.error("[SCHEMA API] Error:", err);
    throw error(500, `Failed to modify schema: ${err.message}`);
  }
};
