#!/usr/bin/env python3
"""
LLM Integration Module for AI Video Generator
Damn, this handles all the LLM API stuff! Don't mess with it unless you know what you're doing!
"""

import os
import json
import time
import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime

class LLMManager:
    """
    LLM API management class - handles all the damn LLM operations
    """

    def __init__(self, config_manager):
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        self.paths = config_manager.get_project_paths()
        # llm_config will be set when needed
        self.llm_config = getattr(config_manager, 'llm_config', None)

        # Setup API clients
        if self.llm_config:
            self._setup_api_clients()

    def set_llm_config(self, llm_config):
        """Set LLM configuration and setup API clients"""
        self.llm_config = llm_config
        if self.llm_config:
            self._setup_api_clients()

    def _setup_api_clients(self):
        """Setup API clients based on configuration"""
        provider = self.llm_config.get('provider', 'qwen')

        if provider == 'qwen':
            import dashscope
            dashscope.api_key = self.llm_config.get('api_key')
            self.client = dashscope
        elif provider == 'openai':
            import openai
            openai.api_key = self.llm_config.get('api_key')
            self.client = openai
        else:
            self.client = None

    def generate_subtitles(self, subtitle_manager) -> bool:
        """Generate subtitles using LLM"""
        # Load prompt content
        prompt_dir = self.paths['prompt']
        prompt_file = prompt_dir / "prompt.md"

        if not prompt_file.exists():
            self.logger.error(f"Prompt file not found: {prompt_file}")
            return False

        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_content = f.read().strip()

            if not prompt_content:
                self.logger.error("Prompt content is empty")
                return False

            self.logger.info(f"Loaded prompt content: {prompt_content[:100]}...")

            # Generate subtitles using LLM
            generated_text = self._call_llm_api(prompt_content)

            if generated_text:
                # Parse generated subtitles
                subtitles = self._parse_generated_subtitles(generated_text)

                if subtitles:
                    # Update subtitle manager
                    subtitle_manager.subtitles = [sub.get('text', '') for sub in subtitles]
                    subtitle_manager.voice_subtitles = subtitles
                    subtitle_manager.display_subtitles = subtitles.copy()

                    # Save generated subtitles
                    self._save_generated_subtitles(subtitles)

                    self.logger.info(f"Generated {len(subtitles)} subtitles")
                    return True
                else:
                    self.logger.error("Failed to parse generated subtitles")
                    return False
            else:
                self.logger.error("LLM API returned empty response")
                # Try fallback method
                return self._fallback_subtitle_generation(subtitle_manager)

        except Exception as e:
            self.logger.error(f"Error generating subtitles: {e}")
            # Try fallback method
            return self._fallback_subtitle_generation(subtitle_manager)

    def _call_llm_api(self, prompt: str) -> Optional[str]:
        """Call LLM API with prompt"""
        provider = self.llm_config.get('provider', 'qwen')

        try:
            if provider == 'qwen':
                return self._call_qwen_api(prompt)
            elif provider == 'grok':
                return self._call_grok_api(prompt)
            elif provider == 'glm':
                return self._call_glm_api(prompt)
            elif provider == 'ollama':
                return self._call_ollama_api(prompt)
            else:
                self.logger.error(f"Unsupported LLM provider: {provider}")
                return None

        except Exception as e:
            self.logger.error(f"Error calling {provider} API: {e}")
            return None

    def _call_qwen_api(self, prompt: str) -> Optional[str]:
        """Call Qwen API via DashScope"""
        import time
        max_retries = 3
        timeout = 60  # Reduced timeout from 300 to 60 seconds

        for attempt in range(max_retries):
            try:
                import dashscope

                messages = [
                    {
                        "role": "system",
                        "content": """You are a professional video subtitle generator. Based on the provided content, generate engaging and natural-sounding subtitles for a short video.

Requirements:
1. Generate 3-8 subtitle lines
2. Each line should be concise (15-50 characters)
3. Content should be engaging and suitable for video
4. Use natural, conversational language
5. Separate each subtitle with a newline

Example format:
Welcome to our amazing video!
Today we'll explore something incredible.
Let's dive right in and discover more."""
                    },
                    {
                        "role": "user",
                        "content": f"Please generate subtitles for a video based on this content:\n\n{prompt}"
                    }
                ]

                # Set timeout for the API call
                import os
                os.environ['DASHSCOPE_CONNECT_TIMEOUT'] = str(timeout)
                os.environ['DASHSCOPE_READ_TIMEOUT'] = str(timeout)

                self.logger.info(f"Calling Qwen API (attempt {attempt + 1}/{max_retries})")
                response = dashscope.Generation.call(
                    model=self.llm_config.get('model', 'qwen-turbo'),
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )

                if response and response.output:
                    generated_text = response.output.text
                    self.logger.info("Qwen API call successful")
                    return generated_text.strip()
                else:
                    self.logger.error(f"Qwen API returned empty response (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return None

            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"Error calling Qwen API (attempt {attempt + 1}): {error_msg}")

                # Check for timeout specifically
                if "timeout" in error_msg.lower() or "connecttimeout" in error_msg.lower():
                    self.logger.warning(f"Network timeout detected (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue

                # For non-timeout errors, don't retry
                if attempt == 0:
                    self.logger.error("Non-timeout error, not retrying")
                    return None

        return None

    def _call_grok_api(self, prompt: str) -> Optional[str]:
        """Call Grok API via litellm"""
        try:
            base_url = self.llm_config.get('base_url')
            headers = self.llm_config.get('headers', {})

            if not base_url:
                self.logger.error("Grok API base URL not configured")
                return None

            messages = [
                {
                    "role": "system",
                    "content": """You are a professional video subtitle generator. Based on the provided content, generate engaging and natural-sounding subtitles for a short video.

Requirements:
1. Generate 3-8 subtitle lines
2. Each line should be concise (15-50 characters)
3. Content should be engaging and suitable for video
4. Use natural, conversational language
5. Separate each subtitle with a newline"""
                },
                {
                    "role": "user",
                    "content": f"Please generate subtitles for a video based on this content:\n\n{prompt}"
                }
            ]

            payload = {
                "model": self.llm_config.get('model', 'grok-code-fast-1'),
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            }

            response = requests.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    generated_text = data['choices'][0]['message']['content']
                    self.logger.info("Grok API call successful")
                    return generated_text.strip()
                else:
                    self.logger.error("Grok API response missing choices")
                    return None
            else:
                self.logger.error(f"Grok API request failed: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"Error calling Grok API: {e}")
            return None

    def _call_glm_api(self, prompt: str) -> Optional[str]:
        """Call GLM API via litellm"""
        try:
            base_url = self.llm_config.get('base_url')
            headers = self.llm_config.get('headers', {})

            if not base_url:
                self.logger.error("GLM API base URL not configured")
                return None

            messages = [
                {
                    "role": "system",
                    "content": """You are a professional video subtitle generator. Based on the provided content, generate engaging and natural-sounding subtitles for a short video.

Requirements:
1. Generate 3-8 subtitle lines
2. Each line should be concise (15-50 characters)
3. Content should be engaging and suitable for video
4. Use natural, conversational language
5. Separate each subtitle with a newline"""
                },
                {
                    "role": "user",
                    "content": f"Please generate subtitles for a video based on this content:\n\n{prompt}"
                }
            ]

            payload = {
                "model": self.llm_config.get('model', 'glm-4.5'),
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            }

            response = requests.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    generated_text = data['choices'][0]['message']['content']
                    self.logger.info("GLM API call successful")
                    return generated_text.strip()
                else:
                    self.logger.error("GLM API response missing choices")
                    return None
            else:
                self.logger.error(f"GLM API request failed: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"Error calling GLM API: {e}")
            return None

    def _call_ollama_api(self, prompt: str) -> Optional[str]:
        """Call Ollama API"""
        try:
            base_url = self.llm_config.get('base_url', 'http://localhost:11434')

            messages = [
                {
                    "role": "system",
                    "content": """You are a professional video subtitle generator. Based on the provided content, generate engaging and natural-sounding subtitles for a short video.

Requirements:
1. Generate 3-8 subtitle lines
2. Each line should be concise (15-50 characters)
3. Content should be engaging and suitable for video
4. Use natural, conversational language
5. Separate each subtitle with a newline"""
                },
                {
                    "role": "user",
                    "content": f"Please generate subtitles for a video based on this content:\n\n{prompt}"
                }
            ]

            payload = {
                "model": self.llm_config.get('model', 'llama3.1'),
                "messages": messages,
                "stream": False
            }

            response = requests.post(
                f"{base_url}/api/chat",
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                if 'message' in data and 'content' in data['message']:
                    generated_text = data['message']['content']
                    self.logger.info("Ollama API call successful")
                    return generated_text.strip()
                else:
                    self.logger.error("Ollama API response missing message content")
                    return None
            else:
                self.logger.error(f"Ollama API request failed: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"Error calling Ollama API: {e}")
            return None

    def _parse_generated_subtitles(self, generated_text: str) -> List[Dict]:
        """Parse generated text into subtitle format"""
        if not generated_text:
            return []

        # Split by newlines and clean up
        lines = [line.strip() for line in generated_text.split('\n') if line.strip()]

        # Filter out very short lines and format
        subtitles = []
        for line in lines:
            # Remove numbering if present
            line = line.lstrip('0123456789.- ')

            # Remove quotes if present
            line = line.strip('"\'')
            line = line.strip('"')  # Double quotes separately

            if len(line) >= 3:  # Minimum length
                subtitles.append({
                    'text': line,
                    'start': 0,  # Will be calculated later
                    'end': 0
                })

        return subtitles

    def _save_generated_subtitles(self, subtitles: List[Dict]) -> None:
        """Save generated subtitles to file"""
        subtitle_dir = self.paths['subtitle']
        output_file = subtitle_dir / "generated_subtitles.txt"

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for subtitle in subtitles:
                    f.write(subtitle['text'] + '\n')

            self.logger.info(f"Generated subtitles saved to: {output_file}")

        except Exception as e:
            self.logger.error(f"Error saving generated subtitles: {e}")

    def test_api_connection(self) -> bool:
        """Test API connection"""
        try:
            # Simple test prompt
            test_prompt = "Hello, please respond with 'Connection test successful'"

            response = self._call_llm_api(test_prompt)

            if response and "successful" in response.lower():
                self.logger.info("API connection test successful")
                return True
            else:
                self.logger.error("API connection test failed")
                return False

        except Exception as e:
            self.logger.error(f"API connection test error: {e}")
            return False

    def get_api_info(self) -> Dict[str, str]:
        """Get API configuration information"""
        return {
            'provider': self.llm_config.get('provider', 'unknown'),
            'model': self.llm_config.get('model', 'unknown'),
            'base_url': self.llm_config.get('base_url', 'none'),
            'has_api_key': bool(self.llm_config.get('api_key'))
        }

    def estimate_token_count(self, text: str) -> int:
        """Estimate token count for text"""
        # Rough estimation: ~1.3 tokens per word for English, ~1.5 tokens per character for Chinese
        if self._contains_chinese(text):
            return len(text) // 2  # Rough estimate for Chinese
        else:
            return len(text.split()) // 2  # Rough estimate for English

    def _contains_chinese(self, text: str) -> bool:
        """Check if text contains Chinese characters"""
        return any('\u4e00' <= char <= '\u9fff' for char in text)

    def _fallback_subtitle_generation(self, subtitle_manager) -> bool:
        """Fallback subtitle generation when API fails"""
        self.logger.info("Attempting fallback subtitle generation...")

        # Try to load existing subtitle files first
        subtitle_dir = self.paths['subtitle']
        existing_files = [
            "subtitles.txt",
            "voice_subtitles.txt",
            "generated_subtitles.txt",
            "custom_subtitles.txt"
        ]

        for filename in existing_files:
            file_path = subtitle_dir / filename
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            # Parse into subtitle format
                            subtitles = self._parse_generated_subtitles(content)
                            if subtitles:
                                subtitle_manager.subtitles = [sub.get('text', '') for sub in subtitles]
                                subtitle_manager.voice_subtitles = subtitles
                                subtitle_manager.display_subtitles = subtitles.copy()
                                self.logger.info(f"Loaded {len(subtitles)} subtitles from {filename}")
                                return True
                except Exception as e:
                    self.logger.warning(f"Failed to load {filename}: {e}")
                    continue

        # If no existing files, generate generic subtitles
        self.logger.info("No existing subtitle files found, generating generic subtitles...")

        generic_subtitles = [
            {'text': 'Welcome to our video presentation', 'start': 0, 'end': 0},
            {'text': 'Enjoy this amazing content', 'start': 0, 'end': 0},
            {'text': 'Thanks for watching', 'start': 0, 'end': 0}
        ]

        subtitle_manager.subtitles = [sub.get('text', '') for sub in generic_subtitles]
        subtitle_manager.voice_subtitles = generic_subtitles
        subtitle_manager.display_subtitles = generic_subtitles.copy()

        # Save generic subtitles
        self._save_generated_subtitles(generic_subtitles)

        self.logger.info(f"Generated {len(generic_subtitles)} generic subtitles")
        return True