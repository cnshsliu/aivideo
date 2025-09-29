#!/usr/bin/env python3
"""
LLM Module - Handles all LLM-related functionality for the AI Video Generator
"""

import os
import sys
import openai
import json
from pathlib import Path
from typing import Optional, Dict, Any

# Import configuration module
from config_module import Config


class LLMManager:
    """
    LLM Manager class - handles all LLM-related operations
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = config.logger

    def get_llm_model_config(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get model configuration for specified LLM provider"""
        return self.config.get_llm_model_config(provider)

    def generate_subtitles(self, args, prompt_folder: Path, subtitle_folder: Path, logger):
        """Generate subtitles using LLM"""
        logger.info("Generating subtitles using LLM...")

        # Read prompt file
        prompt_file = prompt_folder / "prompt.md"
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        # Read the prompt
        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt_content = f.read()

        # Generate subtitles using litellm API
        llm_config = None
        model_name = None
        provider = None
        try:
            # Get LLM configuration from command line argument
            provider = getattr(args, "llm_provider", "qwen")
            llm_config = self.get_llm_model_config(provider)
            if llm_config:
                model_name = llm_config.get("model_name", "unknown")

            # Check if litellm configuration is available
            api_base = os.getenv("LITELLM_API_BASE_URL", "http://localhost:4000")
            api_key = os.getenv("LITELLM_MASTER_KEY")
            if llm_config:
                model_name = llm_config.get("model", "unknown")
            else:
                model_name = "unknown"

            if not api_key:
                raise ValueError(
                    "LITELLM_MASTER_KEY not found in environment variables"
                )

            # Check if provider-specific API key is needed and available
            if llm_config:
                provider_env_key = llm_config.get("env_key")
                if provider_env_key:
                    provider_api_key = os.getenv(provider_env_key)
                    if not provider_api_key:
                        display_name = llm_config.get("display_name", "unknown")
                        raise ValueError(
                            f"{provider_env_key} not found in environment variables (required for {display_name})"
                        )

            if llm_config:
                display_name = llm_config.get("display_name", "unknown")
                logger.info(f"Using LLM provider: {display_name} ({provider})")
            else:
                logger.info(f"Using LLM provider: {provider}")
            logger.info(f"Model: {model_name}")

            # Configure OpenAI client to use litellm endpoint
            original_base_url = openai.base_url
            original_api_key = openai.api_key

            try:
                # Temporarily configure OpenAI client for litellm
                openai.base_url = f"{api_base}/v1/"
                openai.api_key = api_key

                logger.info(f"Using litellm endpoint: {openai.base_url}")

                response = openai.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": """You are a professional subtitle generator for videos. Your task is to create natural, well-timed subtitles based on the given content.

CRITICAL PUNCTUATION REQUIREMENTS:
1. **RESTRICTED PUNCTUATION**: You may ONLY use these four Chinese punctuation marks:
   - Chinese comma: ，
   - Chinese period: 。
   - Chinese question mark: ？
   - Chinese exclamation mark: ！
2. **FORBIDDEN PUNCTUATION**: DO NOT use any other punctuation marks, including:
   - Em dashes: —— (absolutely forbidden)
   - Semicolons: ；；
   - Colons: ：：
   - Parentheses: ()（）
   - Brackets: []【】
   - Quotes: ""''""''
   - Enumeration commas: 、
   - English punctuation: .,!?:;'"`()[]<>
   - Any other special characters or symbols

IMPORTANT REQUIREMENTS:
1. **Natural Breaks**: Break content at natural speaking pauses, commas, periods, or logical stops
2. **Reasonable Length**: Keep subtitles concise (15-45 characters for Chinese, 10-25 words for English)
3. **Speaking Pace**: Each subtitle should take 2-5 seconds to speak naturally
4. **Complete Thoughts**: Don't break in the middle of phrases or ideas
5. **One Line**: Each subtitle should be a single line (no line breaks within subtitles)
6. **CRITICAL**: Include proper punctuation (commas, periods, question marks, exclamation marks) for natural TTS speech synthesis

FORMAT REQUIREMENTS:
- **Sentence Length**: Each complete sentence should be 12-16 Chinese characters long (shorter for mobile screens)
- **Mobile Optimization**: Keep text concise to ensure readability on small mobile screens
- **Sentence Structure**: Combine related concepts into complete, coherent sentences
- **Natural Flow**: Use rich expressions with appropriate modifiers and connecting words
- **Complete Clauses**: Ensure each sentence contains complete meaning expression
- **End with Period**: Every sentence must end with a Chinese period (。)
- **One Sentence Per Line**: Each line should contain one complete sentence
- **Width Constraint**: Ensure text fits within mobile screen width (approximately 20-25 characters maximum)

CONTENT ORGANIZATION:
1. **Combine Related Concepts**: Instead of separating "RTX 5090显卡技术" and "支持大型AI模型运行", combine into "RTX 5090显卡技术支持大型AI模型高效运行"
2. **Use Rich Expressions**: Add appropriate modifiers, connecting words, and complete clause structures
3. **Integrate Technical Points**: Organically combine performance, technology, and advantages into coherent narrative

TONE REQUIREMENTS:
1. **Natural and Fluent**: Avoid mechanical or stiff expressions
2. **Professional and Authoritative**: Highlight technical advantages with expertise
3. **Marketing Language**: Use persuasive language to enhance product appeal
4. **Concise and Powerful**: Keep language clean and impactful for high-end technical product promotion

FORMAT:
- Return each subtitle on a separate line
- No numbering, no extra formatting
- Clean, readable text suitable for TTS and video display

Examples of good subtitles:
"NVIDIA 5090液冷一体机正通过AI技术改变我们的生活。"
"超强AI计算能力为您带来卓越的性能提升和高效的深度学习体验。"
"创新液冷散热系统保持工作环境安静无扰，温度控制精准稳定。"
"RTX 5090显卡技术支持大型AI模型运行，处理复杂任务轻松高效。"
"开箱即用集成管理采用软硬件一体化设计，即插即用便捷体验。"

Remember: Use ONLY Chinese comma (，), period (。), question mark (？), and exclamation mark (！). NO other punctuation allowed.""",
                        },
                        {
                            "role": "user",
                            "content": f"""{prompt_content}

IMPORTANT: When generating subtitles for the above content, you MUST follow these punctuation rules:

- ONLY use: Chinese comma (，), Chinese period (。), Chinese question mark (？), Chinese exclamation mark (！)
- NEVER use: em dashes (——), semicolons (；), colons (：), parentheses, quotes, enumeration commas (、), or any English punctuation
- NO other special characters or symbols allowed

Generate clean, natural subtitles using only the allowed punctuation marks.""",
                        },
                    ],
                )

            finally:
                # Restore original OpenAI configuration
                openai.base_url = original_base_url
                openai.api_key = original_api_key

            # Parse subtitles from response
            subtitles_text = response.choices[0].message.content
            if subtitles_text is None:
                subtitles_text = ""
            raw_subtitles = [
                line.strip() for line in subtitles_text.split("\n") if line.strip()
            ]

            # Store original subtitles for voice generation (with punctuation)
            voice_subtitles = raw_subtitles

            # For display subtitles, remove ending punctuation from each line
            display_subtitles = []
            for subtitle in raw_subtitles:
                # Remove ending punctuation (Chinese period, exclamation mark, question mark, comma)
                if subtitle.endswith(('。', '！', '？', '，')):
                    subtitle = subtitle[:-1]
                display_subtitles.append(subtitle)

            # Save both versions
            voice_file = subtitle_folder / "voice_subtitles.txt"
            display_file = subtitle_folder / "display_subtitles.txt"

            with open(voice_file, "w", encoding="utf-8") as f:
                f.write("\n".join(voice_subtitles))

            with open(display_file, "w", encoding="utf-8") as f:
                f.write("\n".join(display_subtitles))

            logger.info(
                f"Generated {len(voice_subtitles)} voice subtitles and {len(display_subtitles)} display subtitles"
            )

            if llm_config:
                display_name = llm_config.get("display_name", "unknown")
                print(f"Generated {len(display_subtitles)} subtitles using {display_name}")
            else:
                print(f"Generated {len(display_subtitles)} subtitles using {provider}")

            return voice_subtitles, display_subtitles

        except Exception as e:
            print(f"Damn, subtitle generation failed: {e}")
            error_str = str(e).lower()
            if any(
                keyword in error_str
                for keyword in ["api_key", "auth", "unauthorized", "invalid"]
            ):
                print(
                    "This might be an API key issue. Please check your LITELLM_MASTER_KEY in .env file"
                )
                if llm_config and llm_config.get("env_key"):
                    print(
                        f"Also check {llm_config.get('env_key')} for {llm_config.get('display_name', 'unknown')}"
                    )
            elif "rate" in error_str or "limit" in error_str:
                print("This might be a rate limit issue. Please try again later.")
            elif "connection" in error_str or "network" in error_str:
                print(
                    "This might be a network connection issue. Make sure litellm server is running on localhost:4000"
                )
            elif "model_not_found" in error_str or "does not exist" in error_str:
                print(
                    f"This might be a model name issue. Check if {model_name} is available in your litellm config."
                )
            print(
                "ERROR: LLM subtitle generation failed. Cannot continue without valid subtitles."
            )
            print(f"Required environment variables for {provider}:")
            print("- LITELLM_MASTER_KEY: Your litellm master key")
            print(
                "- LITELLM_API_BASE_URL: litellm server URL (default: http://localhost:4000)"
            )
            if llm_config and llm_config.get("env_key"):
                print(
                    f"- {llm_config.get('env_key')}: API key for {llm_config.get('display_name', 'unknown')}"
                )
            else:
                display_name = (
                    llm_config.get("display_name", "unknown")
                    if llm_config
                    else "unknown"
                )
                print(
                    f"- No additional API key needed for {display_name} (local model)"
                )
            print(
                "Make sure litellm server is running: python ~/dev/litellm/litellm.py server"
            )
            sys.exit(1)