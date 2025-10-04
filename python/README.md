# AI Video Generator

A command-line tool to create videos from media materials using AI-generated subtitles and audio.

## Installation

1. Install Python 3.12
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and add your API keys:
   ```bash
   cp .env.example .env
   ```

   Add your API keys to the .env file:
   - `LITELLM_MASTER_KEY`: Required for litellm server authentication
   - `LITELLM_MODEL`: Model name to use (default: qwen3-coder, options: grok-code-fast-1, qwen3-coder, glm-4.5, gpt-oss)
   - `GROK_API_KEY`: Required if using grok-code-fast-1 model
   - `DASHSCOPE_API_KEY`: Required if using qwen3-coder model
   - `Z_API_KEY`: Required if using glm-4.5 model
   - `VOLCENGINE_APP_ID`: Volcengine TTS service App ID (required for audio generation)
   - `VOLCENGINE_ACCESS_TOKEN`: Volcengine TTS access token (required for audio generation)

4. Install FFmpeg (required by MoviePy):
   - Mac: `brew install ffmpeg`
   - Ubuntu: `sudo apt install ffmpeg`
   - Windows: Download from https://ffmpeg.org/

## Usage

```bash
python main.py --folder /path/to/project [options]
```

### Options

- `--folder`: Project folder (required)
- `--sort`: Media pickup order ('alphnum' or 'random', default: 'alphnum')
- `--keep-clip-length`: Keep original clip lengths (default: false)
- `--length`: Target video length in seconds (will be automatically expanded if generated audio is longer)
- `--clip-num`: Number of clips to use
- `--title`: Title text for the beginning
- `--title-length`: Duration to show title (seconds)
- `--title-font`: Font for title
- `--title-position`: Title position (percentage of screen height, default: 20)
- `--subtitle-font`: Font for subtitles
- `--subtitle-position`: Subtitle position (percentage of screen height, default: 80)
- `--clip-silent`: Make each clip silent (default: true)
- `--gen-subtitle`: Generate subtitles using LLM (will also generate voice automatically)
- `--gen-voice`: Generate voice using Volcengine TTS (requires existing subtitles)
- `--llm-provider`: LLM provider for subtitle generation (choices: qwen, grok, glm, ollama; default: qwen)
- `--text FILENAME`: Use specified text file as subtitles (overrides other subtitle sources)

### Project Structure

Your project folder should contain:

```
project_folder/
├── media/
│   ├── start/starting.xxx  # Optional intro video (either name works)
│   ├── clip1.mp4
│   ├── clip2.mp4
│   ├── image1.jpg
│   └── closing.xxx        # Optional outro video
├── prompt/
│   └── prompt.md          # Content for AI subtitle generation (when using --gen-subtitle)
├── subtitle/
│   ├── subtitles1.txt     # Static subtitle files (fallback when no generated subtitles exist)
│   ├── subtitles2.txt     # Multiple .txt files supported (generated_subtitles.txt is ignored)
│   └── generated_subtitles.txt  # Generated subtitles will appear here when using --gen-subtitle
├── logs/
│   ├── video_generation_YYYYMMDD_HHMMSS.log  # Main process log
│   └── subtitles_YYYYMMDD_HHMMSS.txt         # Generated subtitles log
└── output.mp4            # Final generated video
```

### Example

```bash
python main.py --folder example_project \
    --title "Technology,The Future" \
    --length 30 \
    --sort random \
    --clip-num 5

# Generate new subtitles and voice (default: qwen)
python main.py --folder example_project \
    --title "Technology,The Future" \
    --length 30 \
    --gen-subtitle \
    --clip-num 5

# Generate subtitles using different LLM providers
python main.py --folder example_project \
    --title "Technology,The Future" \
    --length 30 \
    --gen-subtitle \
    --llm-provider qwen \
    --clip-num 5

python main.py --folder example_project \
    --title "Technology,The Future" \
    --length 30 \
    --gen-subtitle \
    --llm-provider grok \
    --clip-num 5

python main.py --folder example_project \
    --title "Technology,The Future" \
    --length 30 \
    --gen-subtitle \
    --llm-provider glm \
    --clip-num 5

python main.py --folder example_project \
    --title "Technology,The Future" \
    --length 30 \
    --gen-subtitle \
    --llm-provider ollama \
    --clip-num 5

# Or regenerate voice only (using existing subtitles)
python main.py --folder example_project \
    --title "Technology,The Future" \
    --length 30 \
    --gen-voice \
    --clip-num 5

# Or use custom text file as subtitles
python main.py --folder example_project \
    --title "Technology,The Future" \
    --length 30 \
    --text my_custom_subtitles.txt \
    --gen-voice \
    --clip-num 5
```

## Features

- **AI-powered subtitle generation** using OpenAI API (when using --gen-subtitle)
- **Smart subtitle loading** - automatically uses existing generated_subtitles.txt or static .txt files when not generating
- **Flexible voice generation** - generate voice separately or together with subtitles
- **Custom text file support** - use any text file as subtitles with --text parameter (highest priority)
- **Volcengine TTS integration** - uses Volcengine TTS with Chinese female voice for audio generation
- **Comprehensive logging** - detailed logs of generated subtitles and video creation process
- **Subtitle tracking** - automatic logging and saving of all generated subtitles with metadata
- Automatic audio generation - exits program if TTS fails
- Flexible media processing (videos and images)
- Customizable title and subtitle styling
- Random transition effects
- Support for start/closing clips
- Multiple sorting options for media files

## Notes

- **API Keys**:
  - `LITELLM_MASTER_KEY`: Required for litellm server authentication (when using --gen-subtitle)
  - Provider-specific API keys (choose one based on --llm-provider):
    - `qwen` (default): `DASHSCOPE_API_KEY`
    - `grok`: `GROK_API_KEY`
    - `glm`: `Z_API_KEY`
    - `ollama`: No API key needed (local model)
  - `VOLCENGINE_APP_ID` & `VOLCENGINE_ACCESS_TOKEN`: Required for Volcengine TTS audio generation
- **Generation Flags**:
  - `--text FILENAME`: Use specified text file as subtitles (highest priority, overrides all other subtitle sources)
  - No flags: Use existing generated_subtitles.txt and generated_audio.mp3
  - `--gen-subtitle`: Generate new subtitles + voice (automatically)
  - `--gen-voice`: Generate voice using existing subtitles
  - Both flags: Generate both subtitles and voice
- **Fallback Subtitles**: If no generated_subtitles.txt exists and --text not provided, static .txt files in subtitle folder will be used
- **Audio**: Uses Volcengine TTS with Chinese female voice. Program exits if TTS fails.
- **LLM**: Uses litellm local server for subtitle generation (when using --gen-subtitle). Make sure litellm server is running on localhost:4000
- **Logging**: All generated subtitles are automatically logged and saved to the logs folder with timestamps and metadata
- **Audio-length expansion**: If the generated audio is longer than the specified --length, the video length will be automatically expanded to match the audio duration
- **FFmpeg**: Must be installed and accessible in your PATH
- **Media**: The tool handles both video and image files in the media folder