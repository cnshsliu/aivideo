# Schema Modification Tool

This tool allows for dynamic modification of PostgreSQL table structure through a REST API.

## Features

- Add columns to existing tables
- Drop columns from existing tables
- Modify column types
- Add constraints (primary key, unique, check, not null)
- Drop constraints

## API Endpoint

All operations are performed through the `/api/schema` endpoint using POST requests.

## Usage

### Request Format

```json
{
  "action": "addColumn" | "dropColumn" | "modifyColumn" | "addConstraint" | "dropConstraint",
  "table": "table_name",
  "column": "column_name",
  "type": "data_type",
  "constraintName": "constraint_name",
  "constraintType": "primaryKey" | "unique" | "check" | "notNull",
  "checkExpression": "expression_for_check_constraints",
  "newColumnName": "new_column_name",
  "newName": "new_name_for_column_or_constraint",
  "defaultValue": "default_value",
  "isNullable": boolean
}
```

### Client-side Utility Functions

The tool includes client-side utility functions in `src/lib/schemaUtils.ts` for easier usage:

1. `addColumn(table, column, type, defaultValue?, isNullable?)`
2. `dropColumn(table, column)`
3. `modifyColumn(table, column, type, newName?)`
4. `addConstraint(table, constraintName, constraintType, column?, checkExpression?)`
5. `dropConstraint(table, constraintName)`

### Example Usage

```javascript
import { addColumn, dropColumn } from '$lib/schemaUtils';

// Add a new column
await addColumn('project', 'description', 'TEXT', '', true);

// Drop a column
await dropColumn('project', 'description');
```

## Testing

A test page is available at `/schema-test` to demonstrate the functionality.

## Security Note

This tool allows direct modification of the database schema and should be used with caution. In a production environment, proper authentication and authorization should be implemented.
