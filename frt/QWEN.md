# HKSS Project Context

## Rules

DON'T kill server and DON't try to restart server for debug or test after change
codes, wait user's instructions

## import standard

to import object from local file, import ".js", not ".ts"

## Project Overview

HKSS is a SvelteKit-based web application that provides translation services
using AI models. The application allows users to submit translation tasks which
are processed asynchronously by a continuous batch processor that interfaces
with various Language Model as a Service (MaaS) providers.

### Key Technologies

- **Frontend**: Svelte 5, SvelteKit
- **Backend**: Node.js, TypeScript
- **Database**: PostgreSQL with Drizzle ORM
- **AI Integration**: OpenAI API compatible clients for various MaaS providers
- **Styling**: Tailwind CSS
- **Testing**: Vitest, Playwright
- **Deployment**: Docker for database, Vite for development server

### Core Features

1. **User Authentication**: Session-based authentication with password hashing
   using @node-rs/argon2
2. **Translation Task Management**: Users can submit translation tasks with
   source/target languages
3. **Continuous Task Processing**: Asynchronous processing of translation tasks
   using AI models
4. **Task Queue System**: Priority-based task queue with retry mechanisms
5. **File Management**: Support for various document formats (Markdown, DOCX,
   PDF, PPTX)
6. **Payment System**: Basic payment tracking and management

## Project Structure

```
src/
├── lib/
│   ├── server/
│   │   ├── auth/              # Authentication utilities
│   │   ├── db/                # Database schema and connection
│   │   ├── continuous-batch-processor.ts  # Task processing system
│   │   ├── Agent.ts           # AI model client wrapper
│   │   └── ParallelProcessor.ts  # Parallel task execution utility
│   └── paraglide/            # Internationalization
├── routes/                   # SvelteKit routes (API endpoints and pages)
├── hooks.server.ts           # SvelteKit server hooks
└── app.html                  # Main HTML template
```

## Database Schema

The application uses PostgreSQL with the following key tables:

- **user**: User accounts with authentication
- **session**: User sessions for authentication
- **translation_task**: Translation tasks with status, languages, and content
- **task_queue**: Queue management for processing tasks with priority
- **reference_doc**: Reference documents for translation context
- **payment**: Payment tracking for services

## Task Processing System

The core of the application is the continuous batch processor that:

1. **Polls** the database every 5 seconds for queued tasks
2. **Processes** tasks in parallel using multiple AI model instances
3. **Updates** task status from 'pending' → 'processing' → 'completed'/'failed'
4. **Handles** retries with exponential backoff for failed tasks
5. **Supports** multiple MaaS providers (Qwen, GLM, Kimi)

### Task Flow

1. User submits translation task via API
2. Task is created in `translation_task` table with 'pending' status
3. Task queue entry is created in `task_queue` table with 'queued' status
4. Continuous processor picks up queued tasks
5. AI model translates the content
6. Task status is updated to 'completed' with results or 'failed' with error

## Development Setup

### Prerequisites

- Node.js (version not specified, but modern LTS recommended)
- pnpm (package manager)
- Docker (for PostgreSQL database)

### Environment Variables

Create a `.env` file with:

```
DATABASE_URL="postgres://root:mysecretpassword@localhost:5432/local"
OPENAI_API_KEY="your-api-key"  # For AI model access
```

### Database Setup

1. Start PostgreSQL database:

   ```bash
   npm run db:start
   ```

2. Apply database schema:

   ```bash
   npm run db:push
   ```

### Development Commands

- **Start development server**: `npm run dev`
- **Build for production**: `npm run build`
- **Run tests**: `npm test`
- **Format code**: `npm run format`
- **Lint code**: `npm run lint`
- **Check types**: `npm run check`

### Database Management

- **Generate migrations**: `npm run db:generate`
- **Apply migrations**: `npm run db:migrate`
- **Open database studio**: `npm run db:studio`

## AI Model Integration

The application uses a custom `Agent` class that wraps the OpenAI API client to
interface with various MaaS providers:

- **Qwen3**: Primary model for translation tasks
- **GLM-4.5**: Alternative model from BigModel
- **Kimi**: Alternative model from Moonshot AI

The system automatically handles API key configuration and model selection based
on the provider.

## Testing

The project includes both unit tests (Vitest) and end-to-end tests (Playwright):

- **Unit tests**: `npm run test:unit`
- **E2E tests**: `npm run test:e2e`
- **All tests**: `npm test`

## Deployment

The application is built with SvelteKit's adapter-auto, which automatically
detects the deployment environment. For production deployment:

1. Build the application: `npm run build`
2. Preview the build: `npm run preview`
3. Deploy using your preferred hosting platform

## Common Issues and Solutions

1. **Database Connection Errors**: Ensure Docker is running and the database is
   started with `npm run db:start`
2. **Task Processing Failures**: Check API keys for AI model providers in
   environment variables
3. **Authentication Issues**: Verify database contains valid user records with
   proper password hashes

## Customization Points

1. **AI Models**: Modify the `Agent` class to add new MaaS providers
2. **Task Processing**: Adjust batch size, retry count, and timeout in
   `ContinuousBatchProcessor`
3. **UI Components**: Add new Svelte components in the routes directory
4. **Database Schema**: Extend the schema in `src/lib/server/db/schema.ts`
