/**
 * Schema Modification Utility
 * Provides a simple interface for modifying PostgreSQL table structure
 */

interface SchemaModificationOptions {
  action:
    | 'addColumn'
    | 'dropColumn'
    | 'modifyColumn'
    | 'addConstraint'
    | 'dropConstraint';
  table: string;
  column?: string;
  type?: string;
  constraintName?: string;
  constraintType?: 'primaryKey' | 'unique' | 'check' | 'notNull';
  checkExpression?: string;
  newColumnName?: string;
  newName?: string;
  defaultValue?: any;
  isNullable?: boolean;
}

/**
 * Modify the database schema
 * @param options - The schema modification options
 * @returns A promise that resolves to the response from the API
 */
export async function modifySchema(
  options: SchemaModificationOptions
): Promise<any> {
  try {
    const response = await fetch('/api/schema', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(options)
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Failed to modify schema');
    }

    return await response.json();
  } catch (error) {
    console.error('Error modifying schema:', error);
    throw error;
  }
}

/**
 * Add a new column to a table
 * @param table - The table name
 * @param column - The column name
 * @param type - The column type
 * @param defaultValue - The default value (optional)
 * @param isNullable - Whether the column is nullable (optional, default: true)
 * @returns A promise that resolves to the response from the API
 */
export async function addColumn(
  table: string,
  column: string,
  type: string,
  defaultValue?: any,
  isNullable: boolean = true
): Promise<any> {
  return modifySchema({
    action: 'addColumn',
    table,
    column,
    type,
    defaultValue,
    isNullable
  });
}

/**
 * Drop a column from a table
 * @param table - The table name
 * @param column - The column name
 * @returns A promise that resolves to the response from the API
 */
export async function dropColumn(table: string, column: string): Promise<any> {
  return modifySchema({
    action: 'dropColumn',
    table,
    column
  });
}

/**
 * Modify a column's type
 * @param table - The table name
 * @param column - The column name
 * @param type - The new column type
 * @param newName - The new column name (optional)
 * @returns A promise that resolves to the response from the API
 */
export async function modifyColumn(
  table: string,
  column: string,
  type: string,
  newName?: string
): Promise<any> {
  return modifySchema({
    action: 'modifyColumn',
    table,
    column,
    type,
    newName
  });
}

/**
 * Add a constraint to a table
 * @param table - The table name
 * @param constraintName - The constraint name
 * @param constraintType - The constraint type
 * @param column - The column name (required for primaryKey, unique, and notNull constraints)
 * @param checkExpression - The check expression (required for check constraints)
 * @returns A promise that resolves to the response from the API
 */
export async function addConstraint(
  table: string,
  constraintName: string,
  constraintType: 'primaryKey' | 'unique' | 'check' | 'notNull',
  column?: string,
  checkExpression?: string
): Promise<any> {
  return modifySchema({
    action: 'addConstraint',
    table,
    constraintName,
    constraintType,
    column,
    checkExpression
  });
}

/**
 * Drop a constraint from a table
 * @param table - The table name
 * @param constraintName - The constraint name
 * @returns A promise that resolves to the response from the API
 */
export async function dropConstraint(
  table: string,
  constraintName: string
): Promise<any> {
  return modifySchema({
    action: 'dropConstraint',
    table,
    constraintName
  });
}
