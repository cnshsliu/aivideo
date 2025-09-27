#!/usr/bin/env python3
"""
Configuration Manager for AI Video Generator
Damn, this thing manages all the config stuff! Don't mess with it unless you know what you're doing!
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import dashscope

class ConfigManager:
    """
    Configuration management class - handles all the damn settings
    """

    def __init__(self, project_folder: Path):
        self.project_folder = project_folder
        self.config_file = project_folder / "config.json"
        self.logger = logging.getLogger(__name__)

        # Load environment variables
        load_dotenv()

        # Configure APIs
        dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

        # Default configuration
        self.default_config = {
            "video_settings": {
                "output_width": 1080,
                "output_height": 1920,
                "fps": 30,
                "target_duration": 60,
                "max_clip_duration": 10,
                "fade_duration": 0.5,
                "transition_duration": 0.5
            },
            "audio_settings": {
                "sample_rate": 22050,
                "channels": 2,
                "volume": 0.8,
                "fade_in": 0.1,
                "fade_out": 0.1
            },
            "subtitle_settings": {
                "font_size": 40,
                "font_color": "white",
                "stroke_color": "black",
                "stroke_width": 1,
                "max_chars_per_line": 20,
                "max_lines": 2,
                "position": "bottom",
                "margin": 80
            },
            "api_settings": {
                "llm_provider": "dashscope",
                "llm_model": "qwen-turbo",
                "tts_provider": "volcengine",
                "max_tokens": 2000,
                "temperature": 0.7
            },
            "processing_settings": {
                "use_original_length": False,
                "smart_clip_selection": True,
                "auto_aspect_ratio": True,
                "quality_enhancement": True
            }
        }

        # Load configuration
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # Merge with default config to ensure all keys exist
                merged_config = self.default_config.copy()
                self._deep_merge(merged_config, config)

                self.logger.info(f"Configuration loaded from {self.config_file}")
                return merged_config

            except Exception as e:
                self.logger.error(f"Error loading config file: {e}")
                self.logger.info("Using default configuration")
                return self.default_config.copy()
        else:
            # Create default config file
            self._save_config(self.default_config)
            self.logger.info("Created default configuration file")
            return self.default_config.copy()

    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Deep merge two dictionaries"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            self.logger.error(f"Error saving config file: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        Example: get('video_settings.output_width')
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any) -> None:
        """
        Set configuration value using dot notation
        Example: set('video_settings.output_width', 1920)
        """
        keys = key_path.split('.')
        config = self.config

        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        # Set the value
        config[keys[-1]] = value

        # Save the updated configuration
        self._save_config(self.config)

    def get_video_settings(self) -> Dict[str, Any]:
        """Get video settings"""
        return self.config.get('video_settings', {})

    def get_audio_settings(self) -> Dict[str, Any]:
        """Get audio settings"""
        return self.config.get('audio_settings', {})

    def get_subtitle_settings(self) -> Dict[str, Any]:
        """Get subtitle settings"""
        return self.config.get('subtitle_settings', {})

    def get_api_settings(self) -> Dict[str, Any]:
        """Get API settings"""
        return self.config.get('api_settings', {})

    def get_processing_settings(self) -> Dict[str, Any]:
        """Get processing settings"""
        return self.config.get('processing_settings', {})

    def get_title_settings(self) -> Dict[str, Any]:
        """Get title settings"""
        return {
            'title_font': 'Arial',
            'title_position': 25,  # 25% from top
            'title_duration': 3.0,
            'title_color': 'white',
            'title_stroke_color': 'black',
            'title_stroke_width': 2
        }

    def get_api_key(self, service: str) -> Optional[str]:
        """Get API key for specific service"""
        key_mapping = {
            'dashscope': 'DASHSCOPE_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'volcengine': 'VOLCENGINE_ACCESS_TOKEN',
            'volcengine_app_id': 'VOLCENGINE_APP_ID'
        }

        env_key = key_mapping.get(service)
        if env_key:
            return os.getenv(env_key)
        return None

    def validate_api_keys(self) -> Dict[str, bool]:
        """Validate required API keys"""
        required_keys = {
            'dashscope': self.get_api_key('dashscope'),
            'volcengine': self.get_api_key('volcengine'),
            'volcengine_app_id': self.get_api_key('volcengine_app_id')
        }

        validation_result = {}
        for service, key in required_keys.items():
            validation_result[service] = bool(key)
            if not key:
                self.logger.warning(f"Missing API key for {service}")

        return validation_result

    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values"""
        self._deep_merge(self.config, updates)
        self._save_config(self.config)
        self.logger.info("Configuration updated")

    def reset_to_default(self) -> None:
        """Reset configuration to default values"""
        self.config = self.default_config.copy()
        self._save_config(self.config)
        self.logger.info("Configuration reset to default")

    def get_project_structure(self) -> Dict[str, str]:
        """Get expected project folder structure"""
        return {
            "media": "Media files (videos, images)",
            "prompt": "Text prompts and scripts",
            "subtitle": "Subtitle files",
            "logs": "Log files",
            "output": "Generated videos",
            "config.json": "Configuration file"
        }

    def get_project_paths(self) -> Dict[str, Path]:
        """Get project folder paths"""
        return {
            'project': self.project_folder,
            'media': self.project_folder / "media",
            'prompt': self.project_folder / "prompt",
            'subtitle': self.project_folder / "subtitle",
            'output': self.project_folder / "output",
            'logs': self.project_folder / "logs"
        }

    def validate_project_structure(self) -> bool:
        """Validate project folder structure"""
        required_dirs = ['media', 'prompt', 'subtitle']

        for dir_name in required_dirs:
            dir_path = self.project_folder / dir_name
            if not dir_path.exists():
                self.logger.warning(f"Missing required directory: {dir_name}")
                return False

        self.logger.info("Project structure validated")
        return True

    def clean_and_validate_subtitle(self, subtitle: str) -> str:
        """Clean and validate a single subtitle to ensure it meets requirements"""
        # Remove extra whitespace
        cleaned = subtitle.strip()

        # Ensure it ends with proper punctuation (prefer period)
        if not cleaned.endswith('。') and not cleaned.endswith('！') and not cleaned.endswith('？'):
            cleaned += '。'

        # Clean any other punctuation issues while preserving sentence structure
        cleaned = self._clean_punctuation(cleaned)

        return cleaned

    def remove_trailing_period(self, text: str) -> str:
        """Remove trailing period from text for display subtitles"""
        if text.endswith('。'):
            return text[:-1].strip()
        return text

    def needs_splitting(self, subtitle: str) -> bool:
        """Check if subtitle needs to be split due to length"""
        length = self._calculate_display_length(subtitle)
        return length > 20  # Maximum 20 characters

    def setup_logging(self) -> str:
        """Setup logging configuration"""
        # Create logs directory
        logs_dir = self.project_folder / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Create log filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"video_generation_{timestamp}.log"

        # Configure logging
        import logging
        import sys
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )

        return str(log_file)

    def _clean_punctuation(self, text: str) -> str:
        """Clean punctuation issues in text"""
        # Remove duplicate punctuation
        text = re.sub(r'[。！？]{2,}', lambda m: m.group(0)[0], text)

        # Add space between Chinese and English
        text = re.sub(r'([\u4e00-\u9fff])([a-zA-Z])', r'\1 \2', text)
        text = re.sub(r'([a-zA-Z])([\u4e00-\u9fff])', r'\1 \2', text)

        return text

    def _calculate_display_length(self, text: str) -> int:
        """Calculate display length considering Chinese characters take 2x space"""
        chinese_count = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        english_count = len(text) - chinese_count
        return chinese_count * 2 + english_count