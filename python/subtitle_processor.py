#!/usr/bin/env python3
"""
Subtitle processing module for AI Video Generator
Handles subtitle optimization, validation, and timestamp calculations
"""

import logging
from datetime import datetime
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

    def __init__(self, vg, logger=None):
        """Initialize subtitle processor with optional logger"""
        self.logger = logger or logging.getLogger(__name__)
        self.voice_subtitles = []
        self.display_subtitles = []
        self.subtitle_timestamps = []
        self.subtitle_folder: Optional[Path] = vg.subtitle_folder
        self.audio_file: Optional[Path] = None
        self.display_to_voice_mapping = []
        self.project_folder = vg.project_folder
        self.vg = vg

    def _log_subtitles(self, source="unknown"):
        """Log generated subtitles with detailed information"""
        self.subtitles = self.vg.subtitles
        if not self.subtitles:
            self.logger.warning("No subtitles to log")
            return

        self.logger.info(f"=== GENERATED SUBTILES ({source}) ===")
        self.logger.info(f"Total subtitles: {len(self.subtitles)}")

        for i, subtitle in enumerate(self.subtitles, 1):
            self.logger.info(
                f"Subtitle {i}: '{subtitle}' (length: {len(subtitle)} chars)"
            )

        self.logger.info("=== END SUBTILES ===")

        # Also save subtitles to a dedicated file
        subtitle_file = (
            self.project_folder
            / "logs"
            / f"subtitles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        with open(subtitle_file, "w", encoding="utf-8") as f:
            f.write(f"Generated Subtitles ({source})\n")
            f.write(f"Project: {self.project_folder}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total: {len(self.subtitles)} subtitles\n")
            f.write("=" * 50 + "\n\n")

            for i, subtitle in enumerate(self.subtitles, 1):
                f.write(f"{i}. {subtitle}\n")

        self.logger.info(f"Subtitles saved to: {subtitle_file}")

    def _optimize_subtitles(self, vg, raw_subtitles):
        """Optimize subtitles for display while preserving timing relationships.
        With new LLM prompt requirements, subtitles should already be properly formatted."""
        self.logger.info(f"Optimizing {len(raw_subtitles)} raw subtitles for display")
        if not raw_subtitles:
            return []
        display_subtitles = []
        subtitle_mapping = []  # Maps display subtitle index to original voice subtitle index

        # Set voice subtitles to raw subtitles (preserve original punctuation for voice generation)
        self.voice_subtitles = raw_subtitles

        # Generate display subtitles (without ending punctuation only)
        for idx, voice_subtitle in enumerate(self.voice_subtitles):
            # For display subtitles, remove ending punctuation (Chinese period, exclamation mark, question mark, comma)
            if voice_subtitle.endswith(("。", "！", "？", "，")):
                display_subtitle = voice_subtitle[:-1]
            else:
                display_subtitle = voice_subtitle
            # Split into multiple lines if still too long (fallback)
            if self._needs_splitting(voice_subtitle):
                chunks = self._split_long_subtitle(voice_subtitle)
                # Remove ending punctuation from display chunks
                display_chunks = []
                for chunk in chunks:
                    if chunk.endswith(("。", "！", "？", "，")):
                        display_chunks.append(chunk[:-1])
                    else:
                        display_chunks.append(chunk)
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

        vg.voice_subtitles = self.voice_subtitles
        vg.display_to_voice_mapping = self.display_to_voice_mapping
        vg.display_subtitles = display_subtitles

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

    def _calculate_subtitle_timestamps(self, vg):
        """Calculate intelligent timestamps for display subtitles based on voice subtitles and audio duration"""
        self.subtitle_folder = vg.subtitle_folder
        self.audio_file = vg.audio_file
        self.voice_subtitles = vg.voice_subtitles
        self.display_subtitles = vg.display_subtitles
        self.display_to_voice_mapping = vg.display_to_voice_mapping
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
            vg.subtitle_timestamps = self.subtitle_timestamps
        except Exception as e:
            self.logger.error(f"Failed to calculate subtitle timestamps: {e}")
            self._create_fallback_timestamps()
            vg.subtitle_timestamps = self.subtitle_timestamps

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
            self.vg.subtitle_timestamps = self.subtitle_timestamps
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

    def load_existing_subtitles(self, vg):
        """Load existing subtitles from voice_subtitles.txt and display_subtitles.txt, or fallback to generated_subtitles.txt"""
        # First try to load the dual text system files
        self.subtitle_folder = vg.subtitle_folder
        if not self.subtitle_folder:
            return False

        voice_file = self.subtitle_folder / "voice_subtitles.txt"
        display_file = self.subtitle_folder / "display_subtitles.txt"

        if voice_file.exists() and display_file.exists():
            try:
                # Load voice subtitles
                with open(voice_file, "r", encoding="utf-8") as f:
                    voice_content = f.read().strip()
                    if voice_content:
                        self.voice_subtitles = [
                            line.strip()
                            for line in voice_content.split("\n")
                            if line.strip()
                        ]

                # Load display subtitles
                with open(display_file, "r", encoding="utf-8") as f:
                    display_content = f.read().strip()
                    if display_content:
                        self.display_subtitles = [
                            line.strip()
                            for line in display_content.split("\n")
                            if line.strip()
                        ]

                if self.voice_subtitles and self.display_subtitles:
                    self.subtitles = (
                        self.display_subtitles
                    )  # Use display for main workflow
                    # Create display-to-voice mapping for timestamp calculation
                    self.display_to_voice_mapping = self._create_display_voice_mapping(
                        self.voice_subtitles, self.display_subtitles
                    )
                    print(
                        f"Loaded {len(self.voice_subtitles)} voice subtitles and {len(self.display_subtitles)} display subtitles"
                    )
                    vg.subtiles = self.subtitles
                    vg.voice_subtitles = self.voice_subtitles
                    vg.display_subtitles = self.display_subtitles
                    vg.display_to_voice_mapping = self.display_to_voice_mapping
                    return True
            except Exception as e:
                print(f"Error loading dual text subtitles: {e}")

        # Fallback to old generated_subtitles.txt
        voice_file = self.subtitle_folder / "voice_subtitles.txt"
        if voice_file.exists():
            try:
                with open(voice_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        raw_subtitles = [
                            line.strip() for line in content.split("\n") if line.strip()
                        ]
                        if raw_subtitles:
                            # Create both voice and display versions
                            self.voice_subtitles = raw_subtitles
                            # Create display-optimized subtitles (without unnecessary punctuation)
                            self.display_subtitles = self._optimize_subtitles(
                                self, raw_subtitles
                            )
                            self.subtitles = self.display_subtitles

                            with open(display_file, "w", encoding="utf-8") as f:
                                f.write("\n".join(self.display_subtitles))

                            print(
                                f"Loaded {len(self.voice_subtitles)} voice subtitles and created {len(self.display_subtitles)} display subtitles"
                            )
                            vg.subtiles = self.subtitles
                            vg.voice_subtitles = self.voice_subtitles
                            vg.display_subtitles = self.display_subtitles
                            vg.display_to_voice_mapping = self.display_to_voice_mapping
                            return True
            except Exception as e:
                print(f"Error loading existing subtitles: {e}")

        return False

    def load_text_file_subtitles(self, vg, text_file_path):
        """Load subtitles from specified text file and create voice/display versions"""
        text_file = Path(text_file_path)
        if not text_file.exists():
            raise FileNotFoundError(f"Text file not found: {text_file}")

        self.subtitle_folder = vg.subtitle_folder
        if not self.subtitle_folder:
            return False

        try:
            with open(text_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    # Load original subtitles as voice subtitles (with punctuation)
                    self.voice_subtitles = [
                        line.strip() for line in content.split("\n") if line.strip()
                    ]
                    self.logger.info("voice_subtitles")
                    self.logger.info(self.voice_subtitles)
                    # Create display-optimized subtitles (without unnecessary punctuation)
                    self.display_subtitles = self._optimize_subtitles(
                        vg, self.voice_subtitles
                    )
                    self.logger.info("display_subtitles")
                    self.logger.info(self.display_subtitles)
                    # Use display subtitles for main workflow
                    self.subtitles = self.display_subtitles

                    vg.voice_subtitles = self.voice_subtitles
                    vg.display_subtitles = self.display_subtitles
                    vg.subtitles = self.subtitles

                    if self.voice_subtitles:
                        print(
                            f"Loaded {len(self.voice_subtitles)} voice subtitles and created {len(self.display_subtitles)} display subtitles from {text_file}"
                        )
                        self._log_subtitles(f"text file: {text_file.name}")

                        # Save both versions
                        voice_file = self.subtitle_folder / "voice_subtitles.txt"
                        display_file = self.subtitle_folder / "display_subtitles.txt"

                        with open(voice_file, "w", encoding="utf-8") as f:
                            f.write("\n".join(self.voice_subtitles))

                        with open(display_file, "w", encoding="utf-8") as f:
                            f.write("\n".join(self.display_subtitles))

                        return True
        except Exception as e:
            print(f"Damn, failed to read text file {text_file}: {e}")

        return False
