#!/usr/bin/env python3
"""
Configuration Module - Handles command line arguments, project validation, and logging setup
Damn, don't mess with the config unless you know what you're doing!
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import importlib.util

# Load environment variables (optional)
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # dotenv not available, continue without it
    pass

# Configure APIs (optional)
try:
    import dashscope

    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
except ImportError:
    # dashscope not available, continue without it
    pass

# Enhanced title visibility
ENHANCED_TITLES_AVAILABLE = (
    importlib.util.find_spec("enhanced_title_visibility") is not None
)


class Config:
    """
    Configuration class - handles all the damn config stuff!
    """

    def __init__(self, args):
        """Initialize configuration with parsed arguments"""
        self.args = args
        self.project_folder = Path(args.folder).resolve()
        self.setup_logging()
        self.validate_project_structure()

    def setup_logging(self):
        """Setup logging configuration"""
        logs_dir = self.project_folder / "logs"
        logs_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"video_generation_{timestamp}.log"

        # For --gen1 mode, only log to file, not stdout
        handlers = [logging.FileHandler(log_file, encoding="utf-8")]
        if not getattr(self.args, "gen1", False):
            handlers.append(logging.StreamHandler(sys.stdout))

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=handlers,
        )

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Logging initialized. Log file: {log_file}")

    def validate_project_structure(self):
        """Validate and create required project folders"""
        if not self.project_folder.exists():
            raise ValueError(f"Project folder does not exist: {self.project_folder}")

        required_folders = ["media", "prompt", "subtitle"]
        for folder_name in required_folders:
            folder_path = self.project_folder / folder_name
            folder_path.mkdir(exist_ok=True)

        media_folder = self.project_folder / "media"
        if not any(media_folder.iterdir()):
            self.logger.warning(f"Media folder is empty: {media_folder}")
            raise ValueError(
                f"Media folder is empty: {media_folder}, no media files found"
            )

    def get_llm_model_config(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get model configuration for specified LLM provider"""
        provider_models = {
            "qwen": {
                "model": "qwen3-coder",
                "env_key": "DASHSCOPE_API_KEY",
                "display_name": "Qwen 3 Coder",
            },
            "grok": {
                "model": "grok-code-fast-1",
                "env_key": "GROK_API_KEY",
                "display_name": "Grok Code Fast",
            },
            "glm": {
                "model": "glm-4.5",
                "env_key": "Z_API_KEY",
                "display_name": "GLM 4.5",
            },
            "ollama": {
                "model": "llama3.1",
                "env_key": "OLLAMA_API_KEY",
                "display_name": "Ollama Llama 3.1",
            },
        }

        return provider_models.get(provider)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="AI Video Generator")
    parser.add_argument("--folder", required=True, help="Project folder")
    parser.add_argument(
        "--sort",
        choices=["alphnum", "random"],
        default="alphnum",
        help="Media material pickup order",
    )
    parser.add_argument(
        "--keep-clip-length", action="store_true", help="Keep length of each clip"
    )
    parser.add_argument("--length", type=float, help="Result video length in seconds")
    parser.add_argument("--clip-num", type=int, help="Number of clips")
    parser.add_argument("--title", help="Title text at the beginning")
    parser.add_argument(
        "--keep-title",
        action="store_true",
        help="Keep title text across full video except closing clip",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="open final video",
    )
    parser.add_argument(
        "--title-timestamp",
        action="store_true",
        help="Add timestamp to title",
    )
    parser.add_argument("--title-font", help="Font for title")
    parser.add_argument(
        "--title-font-size", type=int, default=72, help="Title font size (default: 72)"
    )
    parser.add_argument(
        "--title-position",
        type=float,
        default=15,
        help="Title position (percentage of screen height)",
    )
    parser.add_argument("--subtitle-font", help="Font for subtitle")
    parser.add_argument(
        "--subtitle-font-size",
        type=int,
        default=48,
        help="Subtitle font size (default: 48)",
    )
    parser.add_argument(
        "--subtitle-position",
        type=float,
        default=85,
        help="Subtitle position (percentage of screen height)",
    )
    parser.add_argument(
        "--gen-subtitle",
        action="store_true",
        default=False,
        help="Generate subtitles using LLM or static files",
    )
    parser.add_argument(
        "--gen-voice",
        action="store_true",
        default=False,
        help="Generate voice using Volcengine TTS",
    )
    parser.add_argument(
        "--gen1",
        action="store_true",
        default=False,
        help="Generate only subtitles and output to console",
    )
    parser.add_argument(
        "--llm-provider",
        choices=["qwen", "grok", "glm", "ollama"],
        default="qwen",
        help="LLM provider for subtitle generation (default: qwen)",
    )
    parser.add_argument(
        "--text",
        help="Text file to use as subtitles (overrides other subtitle sources)",
    )
    parser.add_argument(
        "--mp3",
        help="Background music MP3 file path",
    )
    parser.add_argument(
        "--bgm-fade-in",
        type=float,
        default=3.0,
        help="Background music fade-in duration in seconds (default: 3.0)",
    )
    parser.add_argument(
        "--bgm-fade-out",
        type=float,
        default=3.0,
        help="Background music fade-out duration in seconds (default: 3.0)",
    )
    parser.add_argument(
        "--bgm-volume",
        type=float,
        default=0.3,
        help="Background music volume level (0.0-1.0, default: 0.3)",
    )
    parser.add_argument(
        "--bodytext",
        help="bodytext file path",
    )
    parser.add_argument(
        "--bodytextlength",
        type=int,
        choices=[0,1,2],
        default=0,
        help="Body text duration (0,1,2, default: 0)",
    )
    parser.add_argument(
        "--bodytext_animation",
        choices=["none", "wipe_down"],
        default="none",
        help="Body text animation type (none, wipe_down, default: none)",
    )
    return parser.parse_args()
