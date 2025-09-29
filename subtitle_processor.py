#!/usr/bin/env python3
"""
Subtitle processing module for AI Video Generator
Handles subtitle optimization, validation, and timestamp calculations
"""

import logging
from pathlib import Path
from typing import Optional

# Import utility functions
from utils_module import (
    clean_punctuation,
    calculate_display_length,
    should_split_mixed_text,
    split_mixed_text,
    split_by_chinese_count,
    estimate_speaking_time,
)


class SubtitleProcessor:
    """Handles all subtitle processing operations"""

    def __init__(self, logger=None):
        """Initialize subtitle processor with optional logger"""
        self.logger = logger or logging.getLogger(__name__)
        self.voice_subtitles = []
        self.display_subtitles = []
        self.subtitle_timestamps = []
        self.subtitle_folder: Optional[Path] = None
        self.audio_file: Optional[Path] = None
        self.display_to_voice_mapping = []

    def _optimize_subtitles(self, raw_subtitles):
        """Optimize subtitles for display while preserving timing relationships.
        With new LLM prompt requirements, subtitles should already be properly formatted."""
        self.logger.info(f"Optimizing {len(raw_subtitles)} raw subtitles for display")
        if not raw_subtitles:
            return []
        display_subtitles = []
        subtitle_mapping = []  # Maps display subtitle index to original voice subtitle index
        # Ensure voice subtitles are properly formatted (with periods)
        cleaned_voice_subtitles = []
        for subtitle in raw_subtitles:
            cleaned_subtitle = self._clean_and_validate_subtitle(subtitle)
            cleaned_voice_subtitles.append(cleaned_subtitle)
        # Update voice subtitles with cleaned versions
        self.voice_subtitles = cleaned_voice_subtitles
        # Generate display subtitles (without trailing periods)
        for idx, voice_subtitle in enumerate(self.voice_subtitles):
            # For display subtitles, remove trailing periods
            display_subtitle = self._remove_trailing_period(voice_subtitle)
            # Split into multiple lines if still too long (fallback)
            if self._needs_splitting(voice_subtitle):
                chunks = self._split_long_subtitle(voice_subtitle)
                # Remove trailing periods from display chunks
                display_chunks = [
                    self._remove_trailing_period(chunk) for chunk in chunks
                ]
                display_subtitles.extend(display_chunks)
                # Each chunk maps to the same original subtitle
                subtitle_mapping.extend([idx] * len(chunks))
            else:
                display_subtitles.append(display_subtitle)
                subtitle_mapping.append(idx)
        self.logger.info(
            f"Generated {len(display_subtitles)} display subtitles from {len(raw_subtitles)} voice subtitles"
        )
        # Store the mapping for later use in timestamp calculation
        self.display_to_voice_mapping = subtitle_mapping
        return display_subtitles

    def _clean_and_validate_subtitle(self, subtitle):
        """Clean and validate a single subtitle to ensure it meets requirements"""
        # Remove extra whitespace
        cleaned = subtitle.strip()
        # Ensure it ends with proper punctuation (prefer period)
        if (
            not cleaned.endswith("。")
            and not cleaned.endswith("！")
            and not cleaned.endswith("？")
        ):
            cleaned += "。"
        # Clean any other punctuation issues while preserving sentence structure
        cleaned = clean_punctuation(cleaned)
        return cleaned

    def _remove_trailing_period(self, text):
        """Remove trailing period from text for display subtitles"""
        if text.endswith("。"):
            return text[:-1].strip()
        return text

    def _needs_splitting(self, subtitle):
        """Check if subtitle needs to be split due to length"""
        length = calculate_display_length(subtitle)
        return length > 20  # Maximum 20 characters

    def _split_long_subtitle(self, subtitle):
        """Split a long subtitle into appropriate chunks"""
        # Try to split at punctuation first
        if should_split_mixed_text(subtitle):
            return split_mixed_text(subtitle, 20)
        else:
            return split_by_chinese_count(subtitle, 20)

    def _calculate_subtitle_timestamps(self):
        """Calculate intelligent timestamps for display subtitles based on voice subtitles and audio duration"""
        if (
            not hasattr(self, "audio_file")
            or self.audio_file is None
            or not self.audio_file.exists()
        ):
            raise ValueError("Audio file not available for timestamp calculation")
        try:
            # Load audio file to get duration
            from moviepy import AudioFileClip

            audio_clip = AudioFileClip(str(self.audio_file))
            total_duration = audio_clip.duration
            audio_clip.close()
            self.logger.info(f"Audio duration: {total_duration:.2f}s")
            self.logger.info(f"Voice subtitles: {len(self.voice_subtitles)}")
            self.logger.info(f"Display subtitles: {len(self.display_subtitles)}")
            # Calculate timing based on voice subtitles (with punctuation)
            voice_estimates = []
            total_voice_time = 0
            for voice_subtitle in self.voice_subtitles:
                estimated_time = estimate_speaking_time(voice_subtitle)
                voice_estimates.append(estimated_time)
                total_voice_time += estimated_time
            self.logger.info(f"Total voice speaking time: {total_voice_time:.2f}s")
            # Adjust voice timing to fit audio duration
            if total_voice_time > total_duration:
                # Scale down to fit
                scale_factor = total_duration / total_voice_time
                self.logger.info(f"Scaling voice timing by factor: {scale_factor:.3f}")
                voice_estimates = [time * scale_factor for time in voice_estimates]
            elif total_voice_time < total_duration:
                # Distribute extra time proportionally
                extra_time = total_duration - total_voice_time
                proportional_extra = [
                    extra_time * (time / total_voice_time) for time in voice_estimates
                ]
                voice_estimates = [
                    voice_estimates[i] + proportional_extra[i]
                    for i in range(len(voice_estimates))
                ]
            # Map voice subtitle timing to display subtitles using the mapping created during optimization
            self.subtitle_timestamps = []
            current_time = 0.0
            for i, display_subtitle in enumerate(self.display_subtitles):
                if i < len(self.display_to_voice_mapping):
                    voice_idx = self.display_to_voice_mapping[i]
                    if voice_idx < len(voice_estimates):
                        duration = voice_estimates[voice_idx]
                    else:
                        # Fallback to equal distribution
                        duration = total_duration / len(self.display_subtitles)
                else:
                    # Fallback to equal distribution
                    duration = total_duration / len(self.display_subtitles)
                start_time = current_time
                end_time = current_time + duration
                self.subtitle_timestamps.append(
                    {
                        "index": i + 1,
                        "text": display_subtitle,
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": duration,
                    }
                )
                current_time = end_time
            self.logger.info(
                f"Created {len(self.subtitle_timestamps)} subtitle timestamps"
            )
            self._create_srt_subtitle_file()
        except Exception as e:
            self.logger.error(f"Failed to calculate subtitle timestamps: {e}")
            self._create_fallback_timestamps()

    def _create_fallback_timestamps(self):
        """Create fallback timestamps with equal distribution based on display subtitles"""
        if (
            not hasattr(self, "audio_file")
            or self.audio_file is None
            or not self.audio_file.exists()
        ):
            return
        try:
            from moviepy import AudioFileClip

            audio_clip = AudioFileClip(str(self.audio_file))
            total_duration = audio_clip.duration
            audio_clip.close()
            self.subtitle_timestamps = []
            duration_per_subtitle = total_duration / len(self.display_subtitles)
            current_time = 0.0
            for i, subtitle in enumerate(self.display_subtitles):
                start_time = current_time
                end_time = current_time + duration_per_subtitle
                self.subtitle_timestamps.append(
                    {
                        "index": i + 1,
                        "text": subtitle,
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": duration_per_subtitle,
                    }
                )
                current_time = end_time
            self.logger.info(
                "Created fallback timestamps with equal distribution for display subtitles"
            )
            self._create_srt_subtitle_file()
        except Exception as e:
            self.logger.error(f"Failed to create fallback timestamps: {e}")

    def _create_display_voice_mapping(self, voice_subtitles, display_subtitles):
        """Create mapping between display and voice subtitles for timestamp calculation"""
        # For existing subtitles, assume 1:1 mapping as a simple fallback
        # This ensures timestamp calculation works correctly
        mapping = []
        for i in range(min(len(display_subtitles), len(voice_subtitles))):
            mapping.append(i)
        # If there are more display subtitles, map them to the last voice subtitle
        while len(mapping) < len(display_subtitles):
            mapping.append(len(voice_subtitles) - 1)
        self.logger.info(
            f"Created display-voice mapping: {len(display_subtitles)} display -> {len(voice_subtitles)} voice"
        )
        return mapping

    def _create_srt_subtitle_file(self):
        """Create SRT subtitle file from timestamps"""
        if not self.subtitle_timestamps or not self.subtitle_folder:
            return
        try:
            srt_file = self.subtitle_folder / "subtitles.srt"
            with open(srt_file, "w", encoding="utf-8") as f:
                for timestamp in self.subtitle_timestamps:
                    # SRT format: index
                    f.write(f"{timestamp['index']}\n")
                    # SRT format: start_time --> end_time
                    start_time = self._format_srt_time(timestamp["start_time"])
                    end_time = self._format_srt_time(timestamp["end_time"])
                    f.write(f"{start_time} --> {end_time}\n")
                    # SRT format: text
                    f.write(f"{timestamp['text']}\n\n")
            self.logger.info(f"SRT subtitles saved to: {srt_file}")
        except Exception as e:
            self.logger.error(f"Failed to create SRT subtitle file: {e}")

    def _format_srt_time(self, seconds):
        """Format seconds to SRT time format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

