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
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

# Configure APIs
import dashscope
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")


class ConfigManager:
    """
    Configuration manager - handles all config-related operations
    Don't even think about touching the config validation logic!
    """

    def __init__(self, args):
        self.args = args
        self.project_folder = Path(args.folder)
        self.media_folder = self.project_folder / "media"
        self.prompt_folder = self.project_folder / "prompt"
        self.subtitle_folder = self.project_folder / "subtitle"

        # Validate project structure
        self._validate_project_structure()

        # Setup logging
        self._setup_logging()

    def _validate_project_structure(self):
        """Validate that the project folder has the required structure"""
        if not self.project_folder.exists():
            raise FileNotFoundError(f"Project folder doesn't exist: {self.project_folder}")

        required_folders = ["media", "prompt", "subtitle"]
        for folder in required_folders:
            if not (self.project_folder / folder).exists():
                (self.project_folder / folder).mkdir(parents=True, exist_ok=True)

    def _setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory
        logs_dir = self.project_folder / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"video_generation_{timestamp}.log"

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Video generation started for project: {self.project_folder}")
        self.logger.info(f"Log file: {log_file}")

    def get_logger(self):
        """Get the logger instance"""
        return self.logger

    def get_project_paths(self):
        """Get all project folder paths"""
        return {
            'project': self.project_folder,
            'media': self.media_folder,
            'prompt': self.prompt_folder,
            'subtitle': self.subtitle_folder,
            'logs': self.project_folder / "logs"
        }

    def get_video_settings(self):
        """Get video processing settings"""
        return {
            'target_width': 1080,
            'target_height': 1920,
            'fps': 30,
            'codec': 'libx264',
            'audio_codec': 'aac'
        }

    def get_title_settings(self):
        """Get title display settings"""
        return {
            'title_font': getattr(self.args, 'title_font', 'Arial'),
            'title_font_size': getattr(self.args, 'title_font_size', 72),
            'title_position': getattr(self.args, 'title_position', 20),
            'title_length': getattr(self.args, 'title_length', 3.0)
        }

    def get_subtitle_settings(self):
        """Get subtitle display settings"""
        return {
            'font': getattr(self.args, 'subtitle_font', 'Arial'),
            'font_size': getattr(self.args, 'subtitle_font_size', 48),
            'position': getattr(self.args, 'subtitle_position', 80)
        }


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="AI Video Generator")

    parser.add_argument("--folder", required=True, help="Project folder")
    parser.add_argument("--sort", choices=['alphnum', 'random'], default='alphnum',
                       help="Media material pickup order")
    parser.add_argument("--keep-clip-length", action="store_true",
                       help="Keep length of each clip")
    parser.add_argument("--length", type=float, help="Result video length in seconds")
    parser.add_argument("--clip-num", type=int, help="Number of clips")
    parser.add_argument("--title", help="Title text at the beginning")
    parser.add_argument("--keep-title", action="store_true",
                       help="Keep title text across full video except closing clip")
    parser.add_argument("--title-length", type=float, help="Seconds to show title")
    parser.add_argument("--title-font", help="Font for title")
    parser.add_argument("--title-font-size", type=int, default=72,
                       help="Title font size (default: 72)")
    parser.add_argument("--title-position", type=float, default=20,
                       help="Title position (percentage of screen height)")
    # Enhanced title options
    parser.add_argument("--title-effect-strength", 
                        choices=['light', 'medium', 'heavy'],
                        default='medium',
                        help="Title effect strength for visibility (default: medium)")
    parser.add_argument("--title-glow", action="store_true",
                        help="Add glowing effect to title for extra visibility")
    parser.add_argument("--subtitle-font", help="Font for subtitle")
    parser.add_argument("--subtitle-font-size", type=int, default=48,
                       help="Subtitle font size (default: 48)")
    parser.add_argument("--subtitle-position", type=float, default=80,
                       help="Subtitle position (percentage of screen height)")
    parser.add_argument("--clip-silent", action="store_true", default=True,
                       help="Make each clip silent (default: True)")
    parser.add_argument("--gen", action="store_true", default=False,
                       help="Generate both subtitles and voice again (ignores existing files)")
    parser.add_argument("--llm-provider", choices=['qwen', 'grok', 'glm', 'ollama'], default='qwen',
                       help="LLM provider for subtitle generation (default: qwen)")
    parser.add_argument("--text", help="Text file to use as subtitles (overrides other subtitle sources)")

    return parser.parse_args()