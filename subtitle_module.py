#!/usr/bin/env python3
"""
Subtitle Generation Module for AI Video Generator
Damn, this handles all the subtitle stuff! Don't mess with it unless you know what you're doing!
"""

import os
import time
import logging
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
from datetime import datetime

try:
    from moviepy.editor import TextClip, CompositeVideoClip, ColorClip
    from moviepy.video.io.VideoFileClip import VideoFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

class SubtitleManager:
    """
    Subtitle management class - handles all the damn subtitle operations
    """

    def __init__(self, config_manager):
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        self.paths = config_manager.get_project_paths()
        # llm_config will be accessed from the main VideoGenerator when needed
        self.llm_config = None

        # Subtitle storage
        self.subtitles: List[str] = []  # Simple list of subtitle texts
        self.voice_subtitles: List[Dict] = []
        self.display_subtitles: List[Dict] = []
        self.subtitle_mapping: Dict[int, Tuple[int, int]] = {}
        self.display_to_voice_mapping: Dict[int, Tuple[int, int]] = {}

    def load_existing_subtitles(self) -> bool:
        """Load existing subtitles from files"""
        subtitle_dir = self.paths['subtitle']
        generated_file = subtitle_dir / "generated_subtitles.txt"

        # Try to load generated subtitles first
        if generated_file.exists():
            try:
                with open(generated_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                self.subtitles = []
                self.voice_subtitles = []
                self.display_subtitles = []

                for line in lines:
                    line = line.strip()
                    if line:
                        # Simple parsing - each line is a subtitle
                        self.subtitles.append(line)
                        self.voice_subtitles.append({'text': line, 'start': 0, 'end': 0})
                        self.display_subtitles.append({'text': line, 'start': 0, 'end': 0})

                self.logger.info(f"Loaded {len(self.voice_subtitles)} subtitles from {generated_file}")
                return True

            except Exception as e:
                self.logger.error(f"Error loading generated subtitles: {e}")

        # Fall back to static subtitle files
        static_files = list(subtitle_dir.glob("*.txt"))
        static_files = [f for f in static_files if f.name != "generated_subtitles.txt"]

        if static_files:
            try:
                self.subtitles = []
                self.voice_subtitles = []
                self.display_subtitles = []

                for file_path in static_files:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()

                    if content:
                        self.subtitles.append(content)
                        self.voice_subtitles.append({'text': content, 'start': 0, 'end': 0})
                        self.display_subtitles.append({'text': content, 'start': 0, 'end': 0})

                self.logger.info(f"Loaded {len(self.voice_subtitles)} subtitles from static files")
                return True

            except Exception as e:
                self.logger.error(f"Error loading static subtitles: {e}")

        return False

    def load_text_file_subtitles(self, text_file_path: str) -> bool:
        """Load subtitles from specified text file"""
        file_path = Path(text_file_path)
        if not file_path.exists():
            self.logger.error(f"Text file not found: {file_path}")
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if content:
                # Split by paragraphs or lines
                paragraphs = re.split(r'\n\s*\n', content)
                if len(paragraphs) == 1:
                    paragraphs = content.split('\n')

                self.subtitles = []
                self.voice_subtitles = []
                self.display_subtitles = []

                for paragraph in paragraphs:
                    paragraph = paragraph.strip()
                    if paragraph:
                        self.voice_subtitles.append({'text': paragraph, 'start': 0, 'end': 0})
                        self.display_subtitles.append({'text': paragraph, 'start': 0, 'end': 0})

                self.logger.info(f"Loaded {len(self.voice_subtitles)} subtitles from text file")
                return True

        except Exception as e:
            self.logger.error(f"Error loading text file subtitles: {e}")

        return False

    def _create_display_voice_mapping(self, voice_subtitles, display_subtitles):
        """Create mapping between voice and display subtitles"""
        mapping = {}
        for i, (voice, display) in enumerate(zip(voice_subtitles, display_subtitles)):
            mapping[i] = (i, i)  # Simple 1:1 mapping for now
        return mapping

    def load_static_subtitles(self) -> bool:
        """Load static subtitle files"""
        subtitle_dir = self.paths['subtitle']
        subtitle_files = list(subtitle_dir.glob("*.txt"))

        # Exclude generated subtitles
        subtitle_files = [f for f in subtitle_files if f.name != "generated_subtitles.txt"]

        if not subtitle_files:
            return False

        self.voice_subtitles = []
        self.display_subtitles = []

        for file_path in subtitle_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()

                if content:
                    self.voice_subtitles.append({'text': content, 'start': 0, 'end': 0})
                    self.display_subtitles.append({'text': content, 'start': 0, 'end': 0})

            except Exception as e:
                self.logger.error(f"Error reading subtitle file {file_path}: {e}")

        if self.voice_subtitles:
            self.subtitle_mapping = self._create_display_voice_mapping(
                self.voice_subtitles, self.display_subtitles
            )
            self.logger.info(f"Loaded {len(self.voice_subtitles)} static subtitles")
            return True

        return False

    def generate_subtitles(self, llm_config=None) -> bool:
        """Generate subtitles using LLM"""
        # Update llm_config if provided
        if llm_config is not None:
            self.llm_config = llm_config

        # Check if we have the llm_module available
        try:
            from llm_module import LLMManager
            llm_manager = LLMManager(self.config)
            if self.llm_config:
                llm_manager.set_llm_config(self.llm_config)
            return llm_manager.generate_subtitles(self)
        except ImportError:
            self.logger.error("LLM module not available for subtitle generation")
            return False

    def calculate_subtitle_timestamps(self, total_duration: float) -> None:
        """Calculate timestamps for subtitles"""
        if not self.voice_subtitles:
            return

        # Estimate speaking time for each subtitle
        total_chars = sum(len(sub['text']) for sub in self.voice_subtitles)
        chars_per_second = total_chars / total_duration if total_duration > 0 else 10

        current_time = 0
        for subtitle in self.voice_subtitles:
            duration = self._estimate_speaking_time(subtitle['text'])
            subtitle['start'] = current_time
            subtitle['end'] = current_time + duration
            current_time += duration

        # Sync display subtitles with voice subtitles - with bounds checking
        for i, display_subtitle in enumerate(self.display_subtitles):
            if i < len(self.voice_subtitles):
                voice_subtitle = self.voice_subtitles[i]
                display_subtitle['start'] = voice_subtitle['start']
                display_subtitle['end'] = voice_subtitle['end']
            else:
                # If there are more display subtitles than voice subtitles,
                # distribute them evenly across the remaining time
                if i > 0 and i - 1 < len(self.display_subtitles):
                    prev_subtitle = self.display_subtitles[i - 1]
                    duration = self._estimate_speaking_time(display_subtitle['text'])
                    display_subtitle['start'] = prev_subtitle['end']
                    display_subtitle['end'] = display_subtitle['start'] + duration

    def _estimate_speaking_time(self, text: str) -> float:
        """Estimate speaking time for text"""
        # Base estimation: ~4 characters per second for Chinese
        # ~150 words per minute for English
        if self._contains_chinese(text):
            # Chinese: ~4 characters per second
            return len(text) / 4.0
        else:
            # English: ~2.5 words per second
            words = len(text.split())
            return words / 2.5

    def _contains_chinese(self, text: str) -> bool:
        """Check if text contains Chinese characters"""
        return any('\u4e00' <= char <= '\u9fff' for char in text)

    def optimize_subtitles(self, raw_subtitles: List[Dict]) -> List[Dict]:
        """Optimize subtitles for better display"""
        optimized = []

        for subtitle in raw_subtitles:
            cleaned = self._clean_and_validate_subtitle(subtitle)
            if cleaned:
                if self._needs_splitting(cleaned):
                    split_subtitles = self._split_long_subtitle(cleaned)
                    optimized.extend(split_subtitles)
                else:
                    optimized.append(cleaned)

        return optimized

    def _clean_and_validate_subtitle(self, subtitle: Dict) -> Optional[Dict]:
        """Clean and validate subtitle"""
        text = subtitle.get('text', '').strip()
        if not text:
            return None

        # Remove trailing period if exists
        text = self._remove_trailing_period(text)

        return {'text': text, 'start': subtitle.get('start', 0), 'end': subtitle.get('end', 0)}

    def _remove_trailing_period(self, text: str) -> str:
        """Remove trailing period from text"""
        return text[:-1] if text.endswith('.') else text

    def _needs_splitting(self, subtitle: Dict) -> bool:
        """Check if subtitle needs to be split"""
        text = subtitle['text']
        return len(text) > 50 or self._should_split_subtitle(text)

    def _should_split_subtitle(self, text: str) -> bool:
        """Check if subtitle should be split based on content"""
        # Split on sentences, clauses, or long phrases
        indicators = [',', '，', '；', ';', '。', '！', '！', '？', '?', '\n']
        return any(indicator in text for indicator in indicators)

    def _split_long_subtitle(self, subtitle: Dict) -> List[Dict]:
        """Split long subtitle into multiple parts"""
        text = subtitle['text']
        start_time = subtitle['start']
        end_time = subtitle['end']

        # Try different splitting methods
        if '\n' in text:
            # Split by newlines
            parts = text.split('\n')
        elif any(punct in text for punct in [',', '，', '；', ';']):
            # Split by punctuation
            parts = self._split_by_punctuation(text)
        elif '——' in text or '—' in text:
            # Split by em dash
            parts = self._split_by_em_dash(text)
        elif self._should_split_mixed_text(text):
            # Split mixed text
            parts = self._split_mixed_text(text)
        elif len(text) > 30:
            # Split by length for very long text
            parts = self._split_by_length(subtitle)
        else:
            # Don't split
            return [subtitle]

        # Create new subtitles with adjusted timestamps
        duration = end_time - start_time
        part_duration = duration / len(parts)

        result = []
        for i, part in enumerate(parts):
            part = part.strip()
            if part:
                new_start = start_time + (i * part_duration)
                new_end = new_start + part_duration
                result.append({'text': part, 'start': new_start, 'end': new_end})

        return result

    def _split_by_punctuation(self, text: str) -> List[str]:
        """Split text by punctuation"""
        punctuation_chars = [',', '，', '；', ';']
        for punct in punctuation_chars:
            if punct in text:
                return [part.strip() for part in text.split(punct) if part.strip()]
        return [text]

    def _split_by_em_dash(self, text: str) -> List[str]:
        """Split text by em dash"""
        for dash in ['——', '—']:
            if dash in text:
                return [part.strip() for part in text.split(dash) if part.strip()]
        return [text]

    def _should_split_mixed_text(self, text: str, max_length: int = 20) -> bool:
        """Check if mixed text should be split"""
        if len(text) <= max_length:
            return False

        has_chinese = self._contains_chinese(text)
        has_english = any(char.isalpha() and not '\u4e00' <= char <= '\u9fff' for char in text)

        return has_chinese and has_english

    def _split_mixed_text(self, text: str, max_length: int = 20) -> List[str]:
        """Split mixed Chinese-English text"""
        if len(text) <= max_length:
            return [text]

        # Try to split at language boundaries
        parts = []
        current_part = ""
        last_chinese = False

        for char in text:
            is_chinese = '\u4e00' <= char <= '\u9fff'

            if current_part and last_chinese != is_chinese and len(current_part) >= 5:
                parts.append(current_part)
                current_part = char
            else:
                current_part += char

            last_chinese = is_chinese

        if current_part:
            parts.append(current_part)

        return parts

    def _split_by_length(self, subtitle: Dict) -> List[Dict]:
        """Split subtitle by length"""
        text = subtitle['text']
        start_time = subtitle['start']
        end_time = subtitle['end']

        # Simple character-based splitting
        max_chars = 25
        if len(text) <= max_chars:
            return [subtitle]

        parts = []
        for i in range(0, len(text), max_chars):
            part = text[i:i + max_chars].strip()
            if part:
                parts.append(part)

        # Distribute time evenly
        duration = end_time - start_time
        part_duration = duration / len(parts)

        result = []
        for i, part in enumerate(parts):
            new_start = start_time + (i * part_duration)
            new_end = new_start + part_duration
            result.append({'text': part, 'start': new_start, 'end': new_end})

        return result

    def _split_subtitle(self, subtitle):
        """Split subtitle at punctuation marks and clean up punctuation"""

        # Special handling for em dash (——) - should be processed first
        if '——' in subtitle:
            parts = self._split_by_em_dash(subtitle)
            if len(parts) > 1:
                # Clean each part (remove unnecessary punctuation)
                cleaned_parts = [self._clean_punctuation(part.strip()) for part in parts if part.strip()]
                # Filter out empty parts and ensure reasonable length
                # But keep transition words like "首先", "其次", etc.
                transition_words = ['首先', '其次', '再次', '最后', '另外', '此外', '同时', '更重要的是', '最重要的是']
                result = []
                for part in cleaned_parts:
                    if len(part) >= 3 or any(part.startswith(word) for word in transition_words):
                        result.append(part)
                if len(result) > 1:
                    return result

        # Comprehensive list of Chinese and English punctuation for splitting
        split_punctuation = [
            '。', '！', '？',  # Chinese sentence endings (keep these)
            '.', '!', '?',     # English sentence endings (keep these)
            '；', ';',        # Semicolons
            '，', ',',        # Commas
            '、',            # Chinese enumeration comma
            '：', ':',        # Colons
            '·', '•',        # Dots/bullets
            '（', '(', '）', ')',  # Parentheses
            '【', '[', '】', ']',   # Brackets
        ]

        # Try splitting with different punctuation
        for punct in split_punctuation:
            if punct in subtitle:
                parts = self._split_by_punctuation(subtitle, punct)
                if len(parts) > 1:
                    return parts

        # If no punctuation found, don't split
        return [subtitle]

    def _split_by_punctuation(self, text, punctuation_char):
        """Split text by punctuation character, preserving the punctuation in the result"""
        parts = []
        current_part = ""

        for char in text:
            current_part += char
            if char == punctuation_char:
                parts.append(current_part)
                current_part = ""

        # Add remaining part
        if current_part.strip():
            parts.append(current_part)

        return parts

    def _split_by_em_dash(self, text):
        """Split text by em dash (——), handling it as a single unit"""
        parts = []
        current_part = ""
        i = 0

        while i < len(text):
            if i + 1 < len(text) and text[i] == '—' and text[i + 1] == '—':
                # Found em dash
                current_part += '——'  # Add the em dash to current part
                parts.append(current_part)
                current_part = ""
                i += 2  # Skip both characters
            else:
                current_part += text[i]
                i += 1

        # Add remaining part
        if current_part.strip():
            parts.append(current_part)

        return parts

    def _clean_punctuation(self, text):
        """Clean up punctuation from text"""
        # Remove trailing punctuation except for sentence endings
        punctuation_chars = '，,、,：,:,;,；,·,•'
        while len(text) > 1 and text[-1] in punctuation_chars:
            text = text[:-1]
        return text

    def _split_by_chinese_count(self, text, max_length):
        """Split text by Chinese character count"""
        if len(text) <= max_length:
            return [text]

        parts = []
        current_part = ""
        current_length = 0

        for char in text:
            # Check if character is Chinese
            if '\u4e00' <= char <= '\u9fff':
                current_length += 1
            else:
                current_length += 0.5  # Non-Chinese characters count as half

            current_part += char

            if current_length >= max_length:
                parts.append(current_part)
                current_part = ""
                current_length = 0

        # Add remaining part
        if current_part.strip():
            parts.append(current_part)

        return parts

    def _split_long_subtitle_text(self, text, max_length=14):
        """Split long subtitle text for display"""
        if len(text) <= max_length:
            return [text]

        # Try to split at spaces or punctuation first
        for i in range(max_length, 0, -1):
            if i < len(text) and text[i] in ' ,，.。!！?？;；':
                return [text[:i], text[i:]]

        # If no good split point, just split at max_length
        return [text[:max_length], text[max_length:]]

    def log_subtitles(self, source: str = "unknown") -> None:
        """Log subtitles to file"""
        logs_dir = self.paths['logs']
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"subtitles_{timestamp}.txt"

        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"Subtitle Generation Log - {source}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write("=" * 50 + "\n\n")

                for i, subtitle in enumerate(self.voice_subtitles):
                    f.write(f"Subtitle {i+1}:\n")
                    f.write(f"  Text: {subtitle['text']}\n")
                    f.write(f"  Start: {subtitle['start']:.2f}s\n")
                    f.write(f"  End: {subtitle['end']:.2f}s\n")
                    f.write(f"  Duration: {subtitle['end'] - subtitle['start']:.2f}s\n")
                    f.write("\n")

            self.logger.info(f"Subtitles logged to {log_file}")

        except Exception as e:
            self.logger.error(f"Error logging subtitles: {e}")

    def get_subtitle_count(self) -> int:
        """Get total number of subtitles"""
        return len(self.voice_subtitles)

    def get_total_subtitle_duration(self) -> float:
        """Get total duration of all subtitles"""
        if not self.voice_subtitles:
            return 0
        return max(sub['end'] for sub in self.voice_subtitles)

    def get_subtitle_text(self, index: int) -> Optional[str]:
        """Get subtitle text by index"""
        if 0 <= index < len(self.voice_subtitles):
            return self.voice_subtitles[index]['text']
        return None

    def has_subtitles(self) -> bool:
        """Check if subtitles are available"""
        return len(self.voice_subtitles) > 0

    def create_srt_subtitle_file(self) -> Optional[str]:
        """Create SRT subtitle file"""
        if not self.voice_subtitles:
            return None

        subtitle_dir = self.paths['subtitle']
        srt_file = subtitle_dir / "subtitles.srt"

        try:
            with open(srt_file, 'w', encoding='utf-8') as f:
                for i, subtitle in enumerate(self.voice_subtitles):
                    start_time = self._format_srt_time(subtitle['start'])
                    end_time = self._format_srt_time(subtitle['end'])

                    f.write(f"{i + 1}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{subtitle['text']}\n\n")

            self.logger.info(f"SRT subtitle file created: {srt_file}")
            return str(srt_file)

        except Exception as e:
            self.logger.error(f"Error creating SRT file: {e}")
            return None

    def _format_srt_time(self, seconds: float) -> str:
        """Format time for SRT file"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"