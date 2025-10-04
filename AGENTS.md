# AI Video Generator Handover Document

## Project Overview

The AI Video Generator is a comprehensive system for creating videos from media materials using AI-generated subtitles and audio. The project consists of two main components:

1. **Python Backend** (`python/`): Command-line tool for video generation using MoviePy, LLM subtitle generation, and TTS
2. **SvelteKit Frontend** (`frt/`): Web interface for project management, media library, and video generation workflow

## Architecture

### Backend (Python)
- **Main Entry Point**: `python/main.py`
- **Core Components**:
  - `videoGenerator.py`: Main video generation logic using MoviePy 2.2.1
  - `llm_module.py`: LLM integration for subtitle generation via LiteLLM
  - `audio_generator.py`: Volcengine TTS integration for voice generation
  - `subtitle_processor.py`: Subtitle processing and timing
  - `background_music.py`: BGM processing with fade in/out
  - `config_module.py`: Configuration parsing and validation
  - `utils_module.py`: Utility functions

### Frontend (SvelteKit)
- **Framework**: Svelte 5 with TypeScript
- **Backend**: SvelteKit server-side capabilities
- **Database**: PostgreSQL with Drizzle ORM
- **Authentication**: Custom session-based auth with Argon2
- **Internationalization**: Paraglide.js (English/Chinese)
- **Styling**: Tailwind CSS
- **Testing**: Vitest + Playwright

## Key Features

### Video Generation
- AI-powered subtitle generation using multiple LLM providers (Qwen, Grok, GLM, Ollama)
- Text-to-speech integration with Volcengine TTS
- Background music processing with customizable fade effects
- Flexible media processing (videos and images)
- Customizable title and subtitle styling
- Random transition effects
- Support for intro/outro clips

### Web Interface
- User authentication and session management
- Project-based workflow management
- Media library with upload capabilities
- Real-time video generation with logging
- Multi-level media organization (public/user/project)
- Configuration management for video generation parameters

## Technology Stack

### Backend Dependencies
```
moviepy==2.2.1
pydub==0.25.1
openai==1.35.7
pillow==10.4.0
ffmpeg-python==0.2.0
click==8.1.7
python-dotenv==1.0.1
dashscope==1.17.5
requests==2.31.0
websockets==12.0
```

### Frontend Dependencies
- **Core**: Svelte 5, TypeScript, SvelteKit
- **Database**: Drizzle ORM, PostgreSQL
- **Auth**: @node-rs/argon2, custom session management
- **Styling**: Tailwind CSS
- **Testing**: Vitest, Playwright
- **Internationalization**: Paraglide.js

## Environment Setup

### Prerequisites
- Python 3.12+
- Node.js 18+
- pnpm package manager
- PostgreSQL (Docker recommended)
- FFmpeg (system installation required)

### Backend Setup
1. Install Python dependencies: `pip install -r python/requirements.txt`
2. Copy `.env.example` to `.env` and configure API keys
3. Install FFmpeg system-wide

### Frontend Setup
1. Install dependencies: `cd frt && pnpm install`
2. Start database: `pnpm db:start`
3. Run migrations: `pnpm db:push`
4. Start development server: `pnpm dev`

### Required Environment Variables
```bash
# LiteLLM Configuration
LITELLM_MASTER_KEY=your_litellm_master_key
LITELLM_API_BASE_URL=http://localhost:4000
LITELLM_MODEL=qwen3-coder

# Provider-specific API Keys
GROK_API_KEY=your_grok_api_key
DASHSCOPE_API_KEY=your_dashscope_api_key
Z_API_KEY=your_zhipu_api_key

# TTS Configuration
VOLCENGINE_APP_ID=your_volcengine_app_id
VOLCENGINE_ACCESS_TOKEN=your_volcengine_access_token

# Database
DATABASE_URL=postgresql://root:mysecretpassword@localhost:5432/local
```

## Project Structure

### Python Backend (`python/`)
```
python/
├── main.py                 # CLI entry point
├── videoGenerator.py       # Core video generation logic
├── llm_module.py           # LLM subtitle generation
├── audio_generator.py      # TTS integration
├── subtitle_processor.py   # Subtitle processing
├── background_music.py     # BGM processing
├── config_module.py        # Configuration management
├── utils_module.py         # Utility functions
├── requirements.txt        # Python dependencies
├── README.md              # Backend documentation
└── CLAUDE.md              # Development guidelines
```

### SvelteKit Frontend (`frt/`)
```
frt/
├── src/
│   ├── lib/
│   │   ├── server/
│   │   │   ├── auth.ts           # Authentication logic
│   │   │   ├── db/               # Database operations
│   │   │   └── continuous-batch-processor.ts
│   │   └── paraglide/            # Internationalization
│   ├── routes/
│   │   ├── +page.svelte         # Main application page
│   │   ├── api/                 # API routes
│   │   └── demo/                # Demo pages
│   ├── hooks.server.ts          # Server hooks
│   └── app.html                 # HTML template
├── package.json
├── svelte.config.js
├── vite.config.ts
├── tailwind.config.js
├── playwright.config.ts
├── vitest-setup-client.ts
├── README.md
└── CLAUDE.md                    # Frontend documentation
```

## Database Schema

The application uses PostgreSQL with the following main entities:
- Users (authentication)
- Projects (video generation projects)
- Media files (uploaded content)
- Sessions (authentication sessions)

Schema defined in: `frt/src/lib/server/db/schema.ts`

## API Endpoints

### Authentication
- `POST /api/auth` - Login/Register
- `POST /api/auth/logout` - Logout
- `GET /api/auth/user` - Get current user

### Projects
- `GET /api/projects` - List user projects
- `POST /api/projects` - Create new project
- `DELETE /api/projects/:id` - Delete project
- `POST /api/projects/:id/copy` - Copy project
- `POST /api/projects/:id/generate` - Generate video

### Media
- `POST /api/media/upload` - Upload media file
- `GET /api/media` - List media files

## Development Workflow

### Backend Development
1. Use MoviePy 2.2.1 with Context7 for API calls
2. Run tests: `python -m pytest` (if test files exist)
3. Lint with ruff: `ruff check`
4. Type check with pyright: `pyright`

### Frontend Development
1. Install dependencies: `pnpm install`
2. Start database: `pnpm db:start`
3. Push schema: `pnpm db:push`
4. Run development server: `pnpm dev`
5. Run tests: `pnpm test`
6. Lint: `pnpm lint`

### Video Generation Usage
```bash
cd python
python main.py --folder /path/to/project [options]
```

Common options:
- `--gen-subtitle`: Generate subtitles using LLM
- `--gen-voice`: Generate voice from subtitles
- `--length`: Target video length in seconds
- `--llm-provider`: LLM provider (qwen/grok/glm/ollama)

## Deployment Considerations

### Production Requirements
- Secure environment variable management
- Database connection pooling
- File storage solution (currently local filesystem)
- CDN for media assets
- Background job processing for video generation
- Monitoring and logging infrastructure

### Security Notes
- Session-based authentication with secure cookies
- Password hashing with Argon2
- API key management for external services
- Input validation and sanitization
- CORS configuration for API access

## Known Issues & Future Improvements

### Current Limitations
- Video generation is synchronous (blocks UI)
- Limited error handling in video generation pipeline
- No video preview before generation
- Basic media organization (public/user/project levels)
- No real-time progress tracking for long-running tasks

### Enhancement Opportunities
- Asynchronous video generation with job queues
- Video preview functionality
- Advanced media management and tagging
- Template system for video styles
- Batch processing capabilities
- Real-time collaboration features
- Analytics and usage tracking

## Testing Strategy

### Backend Testing
- Unit tests for individual modules
- Integration tests for video generation pipeline
- API tests for LLM and TTS integrations

### Frontend Testing
- Unit tests with Vitest (client and server)
- E2E tests with Playwright
- Component testing with Svelte testing library
- always fix neovim diagnostic errors/warning after editting

## Maintenance Tasks

### Regular Maintenance
- Update dependencies (Python and Node.js)
- Monitor API rate limits and costs
- Backup database and media files
- Review and rotate API keys
- Update FFmpeg and system dependencies

### Monitoring
- Video generation success rates
- API response times
- Database performance
- Storage usage and cleanup

## Support & Documentation

### Key Documentation Files
- `python/README.md` - Backend usage and setup
- `frt/CLAUDE.md` - Frontend architecture and guidelines
- `python/CLAUDE.md` - Backend development guidelines
- `.env.example` - Environment variable template

### External Dependencies
- **LiteLLM**: Local LLM server for subtitle generation
- **Volcengine TTS**: Chinese text-to-speech service
- **FFmpeg**: Video processing (system dependency)
- **PostgreSQL**: Database (Docker container)

## Getting Started for New Developers

1. **Clone and setup environment**:
   ```bash
   git clone <repository>
   cd aivideo
   cp .env.example .env
   ```

2. **Setup backend**:
   ```bash
   cd python
   pip install -r requirements.txt
   # Configure .env with API keys
   ```

3. **Setup frontend**:
   ```bash
   cd frt
   pnpm install
   pnpm db:start
   pnpm db:push
   pnpm dev
   ```

4. **Test basic functionality**:
   - Create a user account
   - Upload media files
   - Create a project
   - Generate a simple video

This handover document provides a comprehensive overview of the AI Video Generator project. For detailed implementation specifics, refer to the inline code comments and the CLAUDE.md files in each component directory.

