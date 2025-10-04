[Root Directory](../CLAUDE.md) > **src**

# Source Module

## Module Responsibilities

The `src` module contains the core SvelteKit application code, including:

- Main application entry points and layouts
- Server-side authentication and database logic
- Client-side components and pages
- Internationalization setup and runtime
- Demo implementations of key features

## Entry and Startup

- **HTML Entry**: `/src/app.html` - Main HTML template with language support
- **Root Layout**: `/src/routes/+layout.svelte` - Application layout with CSS
  imports
- **Home Page**: `/src/routes/+page.svelte` - Landing page
- **Server Hooks**: `/src/hooks.server.ts` - Authentication and i18n middleware

## External Interfaces

### Authentication Endpoints

- `/demo/lucia/login` - Login and registration functionality
- `/demo/lucia` - Protected dashboard with logout
- Session management via cookies with 30-day expiry

### Demo Pages

- `/demo` - Feature index page
- `/demo/paraglide` - Internationalization demonstration
- `/demo/lucia` - Authentication demonstration

## Key Dependencies and Configuration

- **Framework**: Svelte 5 with SvelteKit
- **Language**: TypeScript with strict mode
- **Styling**: Tailwind CSS with forms and typography plugins
- **Authentication**: Custom session-based auth with Argon2
- **Database**: PostgreSQL via Drizzle ORM
- **Internationalization**: Paraglide.js runtime
- **Markdown**: mdsvex for `.svx` file support

## Data Models

### User Schema (`/src/lib/server/db/schema.ts`)

```typescript
user: {
  id: text (primary key)
  username: text (unique, not null)
  passwordHash: text (not null)
  age: integer (optional)
}

session: {
  id: text (primary key)
  userId: text (foreign key)
  expiresAt: timestamp (with timezone)
}
```

## Testing and Quality

### Test Locations

- **Unit Tests**: `src/**/*.spec.ts` files
- **E2E Tests**: `e2e/` directory with Playwright
- **Client Tests**: Browser environment with Vitest
- **Server Tests**: Node.js environment

### Quality Tools

- **ESLint**: TypeScript and Svelte-specific rules
- **Prettier**: Code formatting with Svelte plugin
- **TypeScript**: Strict type checking
- **Svelte Check**: Component type validation

## Frequently Asked Questions

### How does authentication work?

The app uses custom session-based authentication:

- Sessions are stored in PostgreSQL with 30-day expiry
- Passwords are hashed using Argon2 with secure parameters
- Session tokens are stored in HTTP-only cookies
- Automatic session renewal when nearing expiry

### How is internationalization implemented?

- Uses Paraglide.js for runtime translation
- Supports English and Chinese languages
- Language switching via client-side JavaScript
- Server-side middleware handles language detection
- Translation files in `/messages/` directory

### What's the database setup?

- PostgreSQL with Docker Compose for development
- Drizzle ORM for type-safe database access
- Schema definitions in TypeScript
- Migration support via Drizzle Kit
- Database studio for visual management

## Related File List

- `/src/app.html` - Main HTML template
- `/src/app.d.ts` - TypeScript declarations
- `/src/routes/+layout.svelte` - Root layout
- `/src/routes/+page.svelte` - Home page
- `/src/lib/server/auth.ts` - Authentication logic
- `/src/lib/server/db/schema.ts` - Database schema
- `/src/hooks.server.ts` - Server middleware
- `/src/lib/paraglide/` - Internationalization runtime

## Change Log (Changelog)

### 2025-09-14 - Initial Documentation

- Created module documentation
- Documented authentication flow
- Added internationalization details
- Included database schema information
- Listed key entry points and interfaces
