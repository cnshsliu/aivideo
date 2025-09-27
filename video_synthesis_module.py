#!/usr/bin/env python3
"""
Video Synthesis Module for AI Video Generator
Damn, this handles all the video synthesis stuff! Don't mess with it unless you know what you're doing!
"""

import time
import subprocess
import random
from pathlib import Path

from moviepy import (
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
    ImageClip,
    vfx,
)

# Import utility functions
from utils_module import (
    get_chinese_compatible_font as get_chinese_font_util,
    contains_chinese,
    split_long_subtitle_text,
    calculate_safe_max_chars,
)


def format_time(seconds):
    """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


class VideoSynthesizer:
    """
    Video synthesis class - handles all the damn video operations for the main application
    """

    def __init__(self, config_manager, media_processor, args, logger):
        self.config = config_manager
        self.media = media_processor
        self.args = args
        self.logger = logger
        self.paths = config_manager.get_project_paths()
        self.video_settings = config_manager.get_video_settings()
        self.render_timeout = max(
            300, int(140 * 5)
        )  # 5x video duration, minimum 5 minutes

        # Add target_width and target_height to video_settings if not present
        if "target_width" not in self.video_settings:
            self.video_settings["target_width"] = 1080
        if "target_height" not in self.video_settings:
            self.video_settings["target_height"] = 1920

        # Initialize attributes that are accessed throughout the class
        self.subtitle_timestamps = []
        self.audio_file = None

    def add_title(self, clip, args, use_full_duration=False):
        """Add title to clip with Chinese font support

        Args:
            clip: The video clip to add title to
            args: The arguments object containing title settings
            use_full_duration: If True, use full clip duration regardless of title_length setting
        """
        self.logger.info(
            f"🔍 DEBUG: VideoSynthesizer.add_title called with title: '{getattr(args, 'title', 'NO TITLE')}'"
        )
        self.logger.info(f"🔍 DEBUG: use_full_duration: {use_full_duration}")
        self.logger.info(
            f"🔍 DEBUG: clip dimensions: {clip.w}x{clip.h}, duration: {clip.duration}"
        )

        if not args.title:
            self.logger.info("🔍 DEBUG: No title provided, returning original clip")
            return clip

        try:
            # Determine title duration
            if use_full_duration:
                title_duration = clip.duration
            else:
                title_duration = getattr(args, "title_length", 3.0)
                if title_duration is None:
                    title_duration = 3.0
                if title_duration > clip.duration:
                    title_duration = clip.duration

            self.logger.info(
                f"Adding title with duration: {title_duration}s to clip of duration: {clip.duration}s"
            )

            # Parse title - split by comma for multi-line
            title_lines = args.title.split(",")
            font_size = getattr(args, "title_font_size", 60)
            if font_size is None:
                font_size = 60
            title_font = getattr(args, "title_font", "Arial-Bold") or "Arial-Bold"

            # Check if title contains Chinese and use appropriate font
            full_title_text = args.title
            if self._contains_chinese(full_title_text):
                self.logger.info(f"Chinese text detected in title: '{full_title_text}'")
                title_font = self._get_chinese_compatible_font(title_font)
                if title_font is None:
                    self.logger.error("No compatible font found for Chinese title text")
                    return clip

            title_clips = []
            title_position = getattr(args, "title_position", 20)
            if title_position is None:
                title_position = 20
            y_offset = title_position / 100 * clip.h

            for i, line in enumerate(title_lines):
                # Adjust font size for subsequent lines
                current_font_size = font_size if i == 0 else int(font_size * 0.9)

                try:
                    # Test if the font is valid by trying to create a small text clip first
                    test_clip = TextClip(
                        text="Test",
                        font=title_font,
                        font_size=12,
                        color="white",
                        stroke_color="black",
                        stroke_width=1,
                    )
                    test_clip.close()

                    # Create the actual title clip
                    title_clip = TextClip(
                        text=line.strip(),
                        font=title_font,
                        font_size=current_font_size,
                        color="white",
                        stroke_color="black",
                        stroke_width=2,
                    )

                    # Verify the clip was created successfully
                    if title_clip is None:
                        raise ValueError("TextClip returned None")

                    # Position the title
                    title_x = clip.w / 2 - title_clip.w / 2
                    title_y = y_offset + i * (current_font_size + 10)

                    if title_clip:
                        positioned_clip = title_clip.with_position((title_x, title_y))
                        # Show title only for the specified duration
                        if positioned_clip:
                            duration_clip = positioned_clip.with_duration(title_duration)
                            if duration_clip:
                                title_clips.append(duration_clip)
                except Exception as text_error:
                    print(
                        f"Damn, title text clip creation failed for line '{line.strip()}': {text_error}"
                    )
                    # Try fallback font
                    try:
                        fallback_font = "Arial"
                        self.logger.info(f"Trying fallback font: {fallback_font}")
                        title_clip = TextClip(
                        text=      line.strip(),
                            font_size=current_font_size,
                            color="white",
                            font=fallback_font,
                            stroke_color="black",
                            stroke_width=2,
                        )

                        if title_clip is None:
                            raise ValueError("Fallback TextClip returned None")

                        # Position the fallback title
                        title_x = clip.w / 2 - title_clip.w / 2
                        title_y = y_offset + i * (current_font_size + 10)

                        if title_clip:
                            positioned_clip = title_clip.with_position((title_x, title_y))
                            if positioned_clip:
                                duration_clip = positioned_clip.with_duration(title_duration)
                                if duration_clip:
                                    title_clips.append(duration_clip)
                        self.logger.info(
                            f"Successfully created title with fallback font for line: '{line.strip()}'"
                        )
                    except Exception as fallback_error:
                        print(
                            f"Damn, fallback title creation also failed: {fallback_error}"
                        )
                        self.logger.error(
                            f"Both title font and fallback failed for line: '{line.strip()}'"
                        )
                        continue

            if not title_clips:
                self.logger.error("No title clips were created successfully")
                return clip

            # Create composite with all title clips
            self.logger.info(
                f"🔍 DEBUG: Creating title_composite with {len(title_clips)} title clips"
            )
            title_composite = CompositeVideoClip(title_clips)
            self.logger.info(
                f"🔍 DEBUG: Title_composite created: {title_composite.w}x{title_composite.h}"
            )

            if use_full_duration:
                # Create final video with title for full duration
                self.logger.info(
                    f"🔍 DEBUG: Creating full-duration title composite with clip ({clip.w}x{clip.h}) and title_composite"
                )
                final_clip = CompositeVideoClip([clip, title_composite])
                self.logger.info(
                    f"🔍 DEBUG: Full-duration composite created: {final_clip.w}x{final_clip.h}"
                )
            else:
                # Create title sequence with background
                title_background = clip.subclip(0, title_duration)
                title_sequence = CompositeVideoClip([title_background, title_composite])

                # Main content without the title portion
                main_content = clip.subclip(title_duration)

                # Concatenate title sequence with main content
                final_clip = concatenate_videoclips([title_sequence, main_content])

            self.logger.info(f"Title added successfully with {len(title_clips)} lines")
            self.logger.info(
                f"🔍 DEBUG: Final clip dimensions: {final_clip.w}x{final_clip.h}, duration: {final_clip.duration}"
            )
            self.logger.info("🔍 DEBUG: Title creation completed successfully")
            return final_clip

        except Exception as e:
            print(f"Damn, title creation failed: {e}")
            self.logger.error(f"Title creation failed: {e}")
            return clip

    def _get_chinese_compatible_font(self, default_font="Arial"):
        """Get a font that supports Chinese characters"""
        return get_chinese_font_util(default_font, self.logger)

    def _contains_chinese(self, text):
        """Check if text contains Chinese characters"""
        return contains_chinese(text)

    def add_subtitles(self, clip, subtitle_text, args):
        """Legacy method: Add single subtitle to clip with Chinese font support"""
        if not subtitle_text:
            return clip

        try:
            font_size = getattr(args, "subtitle_font_size", 48)
            if font_size is None:
                font_size = 48
            subtitle_font = getattr(args, "subtitle_font", "Arial") or "Arial"

            # Check if text contains Chinese and use appropriate font
            if self._contains_chinese(subtitle_text):
                self.logger.info(f"Chinese text detected: '{subtitle_text}'")
                subtitle_font = self._get_chinese_compatible_font(subtitle_font)
                if subtitle_font is None:
                    self.logger.error("No compatible font found for Chinese text")
                    return clip

            self.logger.info(f"Creating subtitle with font: {subtitle_font}")

            # Calculate maximum text width for mobile portrait video with proper margins
            # For 1080px width: 15% margins = 162px each side, text area = 756px
            max_text_width = int(clip.w * 0.65)  # Reduced to 65% for mobile safety

            subtitle_clip = TextClip(
                text=subtitle_text,
                font=subtitle_font,
                font_size=font_size,
                color="white",
                stroke_color="black",
                stroke_width=1,
                size=(max_text_width, None),  # Strict width limit
                method="caption",  # Enable text wrapping
                transparent=True
            )

            # Position subtitle (centered)
            subtitle_position = getattr(args, "subtitle_position", 80)
            if subtitle_position is None:
                subtitle_position = 80
            y_position = subtitle_position / 100 * clip.h
            subtitle_x = clip.w / 2 - subtitle_clip.w / 2
            subtitle_y = y_position

            # Safety check: if text is still too wide, enforce strict limits
            if subtitle_clip.w > max_text_width:
                self.logger.warning(
                    f"Text still too wide after wrapping: {subtitle_clip.w} > {max_text_width}"
                )
                subtitle_clip.close()
                # Try with much smaller font size - more aggressive reduction for mobile
                if self._contains_chinese(subtitle_text):
                    emergency_font_size = max(
                        16, int(font_size * 0.4)
                    )  # 40% reduction for Chinese
                else:
                    emergency_font_size = max(
                        20, int(font_size * 0.6)
                    )  # 40% reduction for English

                self.logger.info(f"Trying emergency font size: {emergency_font_size}")
                subtitle_clip = TextClip(
                    text=subtitle_text,
                    font=subtitle_font,
                    font_size=emergency_font_size,
                    color="white",
                    stroke_color="black",
                    stroke_width=1,
                    size=(max_text_width, None),
                    method="caption",
                    transparent=True
                )

                subtitle_x = clip.w / 2 - subtitle_clip.w / 2
                subtitle_y = y_position

            # Set position and duration
            if subtitle_clip and clip:
                positioned_clip = subtitle_clip.with_position((subtitle_x, subtitle_y))
                if positioned_clip:
                    duration_clip = positioned_clip.with_duration(clip.duration)
                    if duration_clip:
                        # Create composite video
                        final_clip = CompositeVideoClip([clip, duration_clip])
                    else:
                        final_clip = clip
                else:
                    final_clip = clip
            else:
                final_clip = clip if clip else None

            # Create composite video
            final_clip = CompositeVideoClip([clip, subtitle_clip])

            # Clean up
            if subtitle_clip:
                subtitle_clip.close()

            self.logger.info(
                f"Subtitle added successfully at position ({subtitle_x}, {subtitle_y})"
            )
            return final_clip

        except Exception as e:
            print(f"Damn, subtitle creation failed: {e}")
            self.logger.error(f"Subtitle creation failed: {e}")
            return clip

    def add_timestamped_subtitles(self, video_clip):
        """Add subtitles with timestamps to video clip"""
        if not hasattr(self, "subtitle_timestamps") or not self.subtitle_timestamps:
            self.logger.warning(
                "No subtitle timestamps available for timestamped subtitles"
            )
            return self._add_subtitles_fallback(video_clip)

        try:
            subtitle_clips = []
            subtitle_position = getattr(
                self.args, "subtitle_position", 80
            )  # Keep using self.args for timestamped subtitles as it's called from main.py
            if subtitle_position is None:
                subtitle_position = 80
            y_position = subtitle_position / 100 * video_clip.h
            font_size = getattr(
                self.args, "subtitle_font_size", 48
            )  # Keep using self.args for timestamped subtitles as it's called from main.py
            if font_size is None:
                font_size = 48
            subtitle_font = getattr(self.args, "subtitle_font", "Arial") or "Arial"

            # Check if we need Chinese font support
            needs_chinese = False
            for subtitle_info in self.subtitle_timestamps:
                if "text" in subtitle_info and self._contains_chinese(
                    subtitle_info["text"]
                ):
                    needs_chinese = True
                    break

            if needs_chinese:
                subtitle_font = self._get_chinese_compatible_font(subtitle_font)
                if subtitle_font is None:
                    self.logger.error("No compatible font found for Chinese subtitles")
                    return self._add_subtitles_fallback(video_clip)

            # Calculate maximum text width for mobile portrait
            max_text_width = int(video_clip.w * 0.65)

            for subtitle_info in self.subtitle_timestamps:
                try:
                    start_time = subtitle_info.get("start_time", 0)
                    end_time = subtitle_info.get("end_time", start_time + 3)
                    text = subtitle_info.get("text", "")

                    if not text.strip():
                        continue

                    # Validate timing
                    if start_time >= video_clip.duration:
                        continue
                    if end_time > video_clip.duration:
                        end_time = video_clip.duration

                    duration = end_time - start_time
                    if duration <= 0:
                        continue

                    # Create subtitle clip with proper text wrapping
                    subtitle_clip = TextClip(
                        text=text,
                        font_size=font_size,
                        color="white",
                        font=subtitle_font,
                        stroke_color="black",
                        stroke_width=1,
                        size=(max_text_width, None),
                        method="caption",
                        transparent=True
                    )

                    # Set timing and position
                    if subtitle_clip:
                        start_clip = subtitle_clip.with_start(start_time)
                        if start_clip:
                            duration_clip = start_clip.with_duration(duration)
                            if duration_clip:
                                subtitle_x = video_clip.w / 2 - duration_clip.w / 2
                                subtitle_clip = duration_clip.with_position((subtitle_x, y_position))

                    # Add fade effects
                    if subtitle_clip:
                        subtitle_clip = subtitle_clip.with_effects([vfx.FadeIn(0.2), vfx.FadeOut(0.2)])

                    subtitle_clips.append(subtitle_clip)

                except Exception as e:
                    self.logger.warning(
                        f"<<<Failed to create subtitle clip for '{subtitle_info.get('text', '')}': {e}"
                    )
                    continue

            if subtitle_clips:
                final_clip = CompositeVideoClip([video_clip] + subtitle_clips)
                self.logger.info(f"Added {len(subtitle_clips)} timestamped subtitles")
                return final_clip
            else:
                self.logger.warning("No valid subtitle clips created")
                return self._add_subtitles_fallback(video_clip)

        except Exception as e:
            self.logger.error(f"Error adding timestamped subtitles: {e}")
            return self._add_subtitles_fallback(video_clip)

    def _add_subtitles_fallback(self, video_clip):
        """Fallback method to add subtitles when timestamped subtitles fail"""
        try:
            # Get a compatible font
            font = self._get_chinese_compatible_font()

            # Simple static subtitle in the middle
            subtitle_clip = TextClip(
                text="AI Generated Video",
                font=font,
                font_size=30,
                color="yellow",
                stroke_color="black",
                stroke_width=1,
            )

            if subtitle_clip and video_clip:
                positioned_clip = subtitle_clip.with_position(("center", "center"))
                if positioned_clip:
                    duration_clip = positioned_clip.with_duration(video_clip.duration)
                    if duration_clip:
                        return CompositeVideoClip([video_clip, duration_clip])
                elif video_clip:
                    return video_clip
                else:
                    return None
            elif video_clip:
                return video_clip
            else:
                return None

        except Exception as e:
            self.logger.error(f"Error in subtitle fallback: {e}")
            return video_clip

    def apply_transition(self, clip1, clip2):
        """Apply transition between two clips"""
        try:
            # Validate input clips
            if not clip1 or not clip2:
                self.logger.warning(
                    "Invalid clips for transition, using simple concatenation"
                )
                valid_clips = [clip for clip in [clip1, clip2] if clip]
                if valid_clips:
                    return concatenate_videoclips(valid_clips)
                else:
                    raise ValueError("No valid clips for transition")

            # Simple crossfade transition
            transition_duration = 0.5
            clip1_fade = clip1.fadeout(transition_duration)
            clip2_fade = clip2.fadein(transition_duration)

            # Create crossfade
            transition = CompositeVideoClip(
                [clip1_fade, clip2_fade.with_start(clip1.duration - transition_duration)]
            )

            return transition

        except Exception as e:
            self.logger.error(f"Error applying transition: {e}")
            # Fallback to simple concatenation with valid clips only
            valid_clips = [clip for clip in [clip1, clip2] if clip]
            if valid_clips:
                return concatenate_videoclips(valid_clips)
            else:
                raise ValueError("No valid clips for transition")

    def _check_and_regenerate_aspect_ratio(self, video_file):
        """Check video aspect ratio and regenerate if needed"""
        try:
            # Get video info using ffprobe
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-show_entries",
                    "stream=width,height",
                    "-of",
                    "csv=p=0",
                    str(video_file),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                self.logger.error(f"Failed to get video info: {result.stderr}")
                return False

            # Parse width and height
            lines = result.stdout.strip().split("\n")
            if not lines:
                self.logger.error("No video info found")
                return False

            # Get the first video stream
            for line in lines:
                if line.strip():
                    try:
                        width, height = map(int, line.split(","))
                        break
                    except ValueError:
                        continue
            else:
                self.logger.error("Could not parse video dimensions")
                return False

            self.logger.info(f"Current video dimensions: {width}x{height}")

            # Check if we need mobile portrait (9:16) or 16:9
            target_width = self.video_settings["target_width"]
            target_height = self.video_settings["target_height"]

            if target_width == 1080 and target_height == 1920:
                # Mobile portrait target
                return self._regenerate_with_mobile_portrait_ratio(
                    video_file, width, height
                )
            else:
                # 16:9 target
                return self._regenerate_with_16_9_aspect_ratio(
                    video_file, width, height
                )

        except subprocess.TimeoutExpired:  # type: ignore [possibly-unbound]
            self.logger.error("Video info check timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error checking aspect ratio: {e}")
            return False

    def _split_long_subtitle_text(self, text, max_length=14):
        """Split long subtitle text into multiple lines for mobile display"""
        return split_long_subtitle_text(text, max_length)

    def _calculate_safe_max_chars(self, text, max_width_pixels):
        """Calculate safe maximum characters based on character types"""
        return calculate_safe_max_chars(text, max_width_pixels)

    def _regenerate_with_mobile_portrait_ratio(
        self, video_file, current_width, current_height
    ):
        """Regenerate video by cropping from center to 9:16 (width:height) aspect ratio"""
        try:
            import subprocess

            # Create temporary file for the corrected video
            temp_file = video_file.with_suffix(".temp.mp4")

            # Target aspect ratio for mobile portrait: 9:16 (width:height)
            target_ratio = 9 / 16  # 0.5625

            # Calculate crop dimensions to maintain original video ratio
            # We'll crop from the center to get 9:16 aspect ratio
            if current_width / current_height > target_ratio:
                # Video is too wide, crop width
                new_width = int(current_height * target_ratio)
                new_height = current_height
                crop_x = (current_width - new_width) // 2
                crop_y = 0
            else:
                # Video is too tall, crop height
                new_width = current_width
                new_height = int(current_width / target_ratio)
                crop_x = 0
                crop_y = (current_height - new_height) // 2

            self.logger.info(
                f"Cropping video from {current_width}x{current_height} to {new_width}x{new_height}"
            )

            # Use ffmpeg to crop the video
            subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    str(video_file),
                    "-vf",
                    f"crop={new_width}:{new_height}:{crop_x}:{crop_y}",
                    "-c:a",
                    "copy",  # Copy audio without re-encoding
                    "-y",  # Overwrite output file
                    str(temp_file),
                ],
                check=True,
                capture_output=True,
                timeout=300,
            )

            # Replace original file with corrected version
            video_file.unlink()
            temp_file.rename(video_file)

            self.logger.info(
                "Video regenerated with correct mobile portrait aspect ratio"
            )
            print("✅ Video regenerated with correct mobile portrait aspect ratio")

            return True

        except subprocess.CalledProcessError as e:  # type: ignore [possibly-unbound]
            self.logger.error(f"Failed to regenerate video: {e}")
            return False
        except subprocess.TimeoutExpired:  # type: ignore [possibly-unbound]
            self.logger.error("Video regeneration timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error regenerating video: {e}")
            return False

    def _regenerate_with_16_9_aspect_ratio(
        self, video_file, current_width, current_height
    ):
        """Regenerate video by cropping from center to 16:9 aspect ratio"""
        try:
            import subprocess

            # Create temporary file for the corrected video
            temp_file = video_file.with_suffix(".temp.mp4")

            # Target aspect ratio: 16:9
            target_ratio = 16 / 9

            # Calculate crop dimensions to maintain original video ratio
            # We'll crop from the center to get 16:9 aspect ratio
            if current_width / current_height > target_ratio:
                # Video is too wide, crop width
                new_width = int(current_height * target_ratio)
                new_height = current_height
                crop_x = (current_width - new_width) // 2
                crop_y = 0
            else:
                # Video is too tall, crop height
                new_width = current_width
                new_height = int(current_width / target_ratio)
                crop_x = 0
                crop_y = (current_height - new_height) // 2

            self.logger.info(
                f"Cropping video from {current_width}x{current_height} to {new_width}x{new_height}"
            )

            # Use ffmpeg to crop the video
            subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    str(video_file),
                    "-vf",
                    f"crop={new_width}:{new_height}:{crop_x}:{crop_y}",
                    "-c:a",
                    "copy",  # Copy audio without re-encoding
                    "-y",  # Overwrite output file
                    str(temp_file),
                ],
                check=True,
                capture_output=True,
                timeout=300,
            )

            # Replace original file with corrected version
            video_file.unlink()
            temp_file.rename(video_file)

            self.logger.info("Video regenerated with correct 16:9 aspect ratio")
            print("✅ Video regenerated with correct 16:9 aspect ratio")

            return True

        except subprocess.CalledProcessError as e:  # type: ignore [possibly-unbound]
            self.logger.error(f"Failed to regenerate video: {e}")
            return False
        except subprocess.TimeoutExpired:  # type: ignore [possibly-unbound]
            self.logger.error("Video regeneration timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error regenerating video: {e}")
            return False

    def _create_srt_subtitle_file(self):
        """Create SRT subtitle file with calculated timestamps"""
        if not hasattr(self, "subtitle_timestamps") or not self.subtitle_timestamps:
            self.logger.error("No subtitle timestamps available for SRT file creation")
            return False

        try:
            srt_file_path = self.paths["subtitle"] / "subtitles.srt"

            with open(srt_file_path, "w", encoding="utf-8") as f:
                for subtitle_info in self.subtitle_timestamps:
                    # SRT format:
                    # 1
                    # 00:00:01,000 --> 00:00:04,000
                    # Hello world

                    index = subtitle_info["index"]
                    start_time = subtitle_info["start_time"]
                    end_time = subtitle_info["end_time"]
                    text = subtitle_info["text"]

                    # Convert seconds to SRT time format (HH:MM:SS,mmm)
                    start_str = format_time(start_time)
                    end_str = format_time(end_time)

                    # Write subtitle entry
                    f.write(f"{index}\n")
                    f.write(f"{start_str} --> {end_str}\n")
                    f.write(f"{text}\n\n")

            self.logger.info(f"Created SRT subtitle file: {srt_file_path}")
            self.logger.info(f"Total subtitles: {len(self.subtitle_timestamps)}")

            # Log first few subtitles for verification
            for i in range(min(3, len(self.subtitle_timestamps))):
                sub = self.subtitle_timestamps[i]
                start_str = format_time(sub["start_time"])
                end_str = format_time(sub["end_time"])
                self.logger.info(
                    f"Subtitle {i + 1}: {start_str} --> {end_str} | '{sub['text']}'"
                )

            return True

        except Exception as e:
            self.logger.error(f"Failed to create SRT subtitle file: {e}")
            return False

    def process_media_clips(self, media_files, args):
        """Process media clips according to specifications"""
        if not media_files:
            raise ValueError("No media files found")

        self.logger.info(
            f"Processing media clips with args.length: {getattr(args, 'length', 'None')}"
        )
        self.logger.info(f"Available media files: {len(media_files)}")

        # Determine how many clips to use
        clip_num = len(media_files)
        if args.clip_num and args.clip_num > 0:
            clip_num = min(args.clip_num, len(media_files))

        selected_clips = media_files[:clip_num]
        self.logger.info(f"Selected {len(selected_clips)} clips for processing")

        if args.keep_clip_length:
            # Keep original clip lengths
            self.logger.info("Using keep_clip_length mode")
            return self._process_with_original_length(selected_clips, args)
        else:
            # Check if we have a target length
            target_length = getattr(args, "length", None)
            self.logger.info(f"Target length check: {target_length}")
            if target_length:
                # Cut clips to fit target length
                self.logger.info("Using target length mode")
                return self._process_with_target_length(selected_clips, target_length)
            else:
                # No target length specified - keep original lengths
                self.logger.info(
                    "No target length specified, keeping original clip lengths"
                )
                return self._process_with_original_length(selected_clips, args)

    def _resize_to_mobile_aspect_ratio(self, clip):
        """Resize video clip to mobile portrait 9:16 aspect ratio with center scaling"""
        return self.media._resize_to_mobile_aspect_ratio(clip)

    def _safe_load_video_clip(self, file_path, max_duration_check=10.0):
        """Safely load a video clip with error handling for corrupted files"""
        return self.media._safe_load_video_clip(file_path, max_duration_check)

    def _safe_concatenate_clips(self, clips, method="compose"):
        """Safely concatenate clips with robust error handling"""
        return self.media._safe_concatenate_clips(clips, method)

    def _process_with_original_length(self, clips, args):
        """Process clips keeping their original length"""
        processed_clips = []
        target_length = getattr(args, "length", None)

        self.logger.info(
            f"Starting _process_with_original_length with target_length: {target_length}"
        )

        # First pass: process all clips normally
        for i, clip_path in enumerate(clips):
            try:
                if clip_path.suffix.lower() in {
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".gif",
                    ".bmp",
                    ".tiff",
                }:
                    # Convert image to video clip
                    clip = ImageClip(str(clip_path)).with_duration(3.0)
                    # Resize image to mobile aspect ratio
                    clip = self._resize_to_mobile_aspect_ratio(clip)
                    self.logger.debug(
                        f"Converted and resized image to clip: {clip_path} (3.0s)"
                    )
                else:
                    # Video clip with safe loading for corrupted files
                    clip = self._safe_load_video_clip(clip_path)
                    if clip is None:
                        self.logger.warning(
                            f"Skipping corrupted video clip: {clip_path}"
                        )
                        continue
                    # Resize video clip to fit mobile aspect ratio (remove black borders)
                    clip = self._resize_to_mobile_aspect_ratio(clip)
                    self.logger.debug(
                        f"Loaded and resized video clip: {clip_path} ({clip.duration:.2f}s -> {clip.w}x{clip.h})"
                    )

                # Make clip silent if requested
                if getattr(self.args, "clip_silent", False):
                    clip = clip.without_audio()

                processed_clips.append(clip)

                # Stop if we've exceeded target length
                total_duration = sum(c.duration for c in processed_clips)
                if target_length and total_duration >= target_length:
                    self.logger.info(
                        f"Reached target length {target_length}s at clip {i + 1}, stopping clip processing"
                    )
                    break

            except Exception as e:
                self.logger.error(f"Failed to process {clip_path}: {e}")
                continue

        total_duration = sum(c.duration for c in processed_clips)
        self.logger.info(
            f"After initial processing: {len(processed_clips)} clips with total duration: {total_duration:.2f}s"
        )

        # If we have a target length and haven't reached it, extend by repeating clips
        if target_length and total_duration < target_length and processed_clips:
            needed_extension = target_length - total_duration
            self.logger.info(
                f"Need to extend video by {needed_extension:.2f}s to reach target of {target_length}s"
            )

            remaining_duration = needed_extension
            clip_index = 0
            original_clip_count = len(processed_clips)

            while (
                remaining_duration > 0.01 and processed_clips
            ):  # Use small threshold to avoid infinite loops
                # Repeat clips to fill the remaining duration
                clip_to_repeat = processed_clips[clip_index % original_clip_count]

                if (
                    clip_to_repeat.duration <= remaining_duration + 0.01
                ):  # Small tolerance
                    # Use the entire clip
                    repeated_clip = clip_to_repeat.copy()
                    processed_clips.append(repeated_clip)
                    remaining_duration -= clip_to_repeat.duration
                    self.logger.debug(
                        f"Added full clip {clip_index % original_clip_count + 1} ({clip_to_repeat.duration:.2f}s), remaining: {remaining_duration:.2f}s"
                    )
                else:
                    # Use part of the clip
                    partial_clip = clip_to_repeat.subclip(0, remaining_duration)
                    processed_clips.append(partial_clip)
                    self.logger.debug(
                        f"Added partial clip ({remaining_duration:.2f}s) from clip {clip_index % original_clip_count + 1}"
                    )
                    remaining_duration = 0

                clip_index += 1

                # Safety check to prevent infinite loops
                if clip_index > original_clip_count * 10:  # Max 10 full cycles
                    self.logger.warning(
                        "Reached safety limit for clip repetition, stopping extension"
                    )
                    break

        total_duration = sum(c.duration for c in processed_clips)
        self.logger.info(
            f"Final _process_with_original_length: {len(processed_clips)} clips with total duration: {total_duration:.2f}s"
        )

        if target_length:
            self.logger.info(
                f"Target vs Actual: {target_length:.2f}s vs {total_duration:.2f}s (diff: {abs(target_length - total_duration):.2f}s)"
            )

        return processed_clips

    def _process_with_target_length(self, clips, target_length):
        """Process clips to fit target length"""
        if not target_length:
            raise ValueError(
                "Target length must be specified when not keeping clip length"
            )

        self.logger.info(f"Processing clips to fit target length: {target_length}s")
        clip_duration = target_length / len(clips)
        self.logger.info(f"Each clip will be: {clip_duration:.2f}s")

        processed_clips = []

        for clip_path in clips:
            try:
                if clip_path.suffix.lower() in {
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".gif",
                    ".bmp",
                    ".tiff",
                }:
                    # Convert image to video clip
                    clip = ImageClip(str(clip_path)).with_duration(clip_duration)
                    # Resize image to mobile aspect ratio
                    clip = self._resize_to_mobile_aspect_ratio(clip)
                    self.logger.debug(
                        f"Created and resized image clip: {clip_path} ({clip_duration:.2f}s -> {clip.w}x{clip.h})"
                    )
                else:
                    # Video clip - process to exact duration with safe loading
                    full_clip = self._safe_load_video_clip(clip_path)
                    if full_clip is None:
                        self.logger.warning(
                            f"Skipping corrupted video clip: {clip_path}"
                        )
                        continue

                    # Resize the full clip to mobile aspect ratio before processing
                    full_clip = self._resize_to_mobile_aspect_ratio(full_clip)
                    self.logger.debug(
                        f"Resized video clip to mobile aspect ratio: {clip_path} ({full_clip.w}x{full_clip.h})"
                    )

                    if full_clip.duration >= clip_duration:
                        # Trim to exact duration
                        start_time = random.uniform(
                            0, full_clip.duration - clip_duration
                        )
                        clip = full_clip.subclip(start_time, start_time + clip_duration)
                        self.logger.debug(
                            f"Trimmed video clip: {clip_path} ({clip_duration:.2f}s from {start_time:.2f}s)"
                        )
                    else:
                        # Clip is shorter than target duration - need to extend it
                        remaining_duration = clip_duration - full_clip.duration
                        extended_clips = [full_clip]

                        # Safety check for invalid remaining duration
                        if remaining_duration <= 0:
                            self.logger.warning(
                                f"Invalid remaining duration: {remaining_duration:.2f}s for {clip_path}"
                            )
                            clip = full_clip
                        else:
                            # Keep repeating the clip to fill the remaining duration
                            self.logger.info(
                                f"Extending clip {clip_path} from {full_clip.duration:.2f}s to {clip_duration:.2f}s"
                            )

                            # Maximum repetitions to prevent infinite loops - be more conservative
                            max_repetitions = (
                                int(clip_duration / full_clip.duration) + 1
                            )
                            if (
                                max_repetitions > 20
                            ):  # Hard limit to prevent excessive repetitions
                                max_repetitions = 20
                            repetition_count = 0

                            while (
                                remaining_duration > 0.01
                                and repetition_count < max_repetitions
                            ):
                                repetition_count += 1

                                if (
                                    full_clip.duration <= remaining_duration + 0.01
                                ):  # Add small tolerance
                                    # Use full clip again
                                    try:
                                        repeated_clip = full_clip.copy()
                                        # Verify the copied clip has valid duration
                                        if (
                                            hasattr(repeated_clip, "duration")
                                            and repeated_clip.duration > 0
                                        ):
                                            extended_clips.append(repeated_clip)
                                            remaining_duration -= repeated_clip.duration
                                            self.logger.debug(
                                                f"Repeated full clip {clip_path} ({repetition_count}), remaining: {remaining_duration:.2f}s"
                                            )
                                        else:
                                            self.logger.warning(
                                                f"Invalid copied clip duration for {clip_path}"
                                            )
                                            break
                                    except Exception as copy_error:
                                        self.logger.error(
                                            f"Failed to copy clip {clip_path}: {copy_error}"
                                        )
                                        break
                                else:
                                    # Use partial clip - add safety checks
                                    try:
                                        # Ensure we don't exceed the clip duration
                                        safe_end_time = min(
                                            remaining_duration, full_clip.duration
                                        )
                                        if (
                                            safe_end_time > 0.01
                                        ):  # Minimum duration check
                                            partial_clip = full_clip.subclip(
                                                0, safe_end_time
                                            )
                                            # Verify the partial clip is valid
                                            if (
                                                hasattr(partial_clip, "duration")
                                                and partial_clip.duration > 0
                                            ):
                                                extended_clips.append(partial_clip)
                                                self.logger.debug(
                                                    f"Added partial clip ({safe_end_time:.2f}s) from {clip_path}"
                                                )
                                            else:
                                                self.logger.warning(
                                                    f"Invalid partial clip created from {clip_path}"
                                                )
                                                # Use full clip as fallback
                                                extended_clips.append(full_clip.copy())
                                                remaining_duration -= full_clip.duration
                                        else:
                                            self.logger.warning(
                                                f"Invalid safe_end_time: {safe_end_time:.2f}s"
                                            )
                                            break
                                    except Exception as subclip_error:
                                        self.logger.error(
                                            f"Failed to create subclip from {clip_path}: {subclip_error}"
                                        )
                                        # Use full clip as fallback
                                        try:
                                            extended_clips.append(full_clip.copy())
                                            remaining_duration -= full_clip.duration
                                        except Exception as fallback_error:
                                            self.logger.error(
                                                f"Fallback also failed for {clip_path}: {fallback_error}"
                                            )
                                            break

                                remaining_duration = max(
                                    0, remaining_duration
                                )  # Ensure non-negative

                            # Concatenate all extended clips with error handling
                            if len(extended_clips) > 1:
                                try:
                                    # Verify all clips have valid durations before concatenation
                                    valid_clips = []
                                    for i, extended_clip in enumerate(extended_clips):
                                        if (
                                            hasattr(extended_clip, "duration")
                                            and extended_clip.duration > 0
                                        ):
                                            valid_clips.append(extended_clip)
                                        else:
                                            self.logger.warning(
                                                f"Skipping invalid extended clip {i} from {clip_path}"
                                            )

                                    if len(valid_clips) > 0:
                                        clip = self._safe_concatenate_clips(
                                            valid_clips, method="compose"
                                        )
                                        self.logger.info(
                                            f"Successfully extended video clip: {clip_path} (original: {full_clip.duration:.2f}s, extended: {clip.duration:.2f}s)"
                                        )
                                    else:
                                        self.logger.error(
                                            f"No valid clips to concatenate for {clip_path}"
                                        )
                                        clip = full_clip  # Fallback to original

                                except Exception as concat_error:
                                    self.logger.error(
                                        f"Failed to concatenate extended clips for {clip_path}: {concat_error}"
                                    )
                                    # Fallback to original clip
                                    clip = full_clip
                            else:
                                clip = (
                                    extended_clips[0] if extended_clips else full_clip
                                )

                # Make clip silent if requested
                if getattr(self.args, "clip_silent", False):
                    clip = clip.without_audio()

                processed_clips.append(clip)

            except Exception as e:
                self.logger.error(f"Failed to process {clip_path}: {e}")
                continue

        total_duration = sum(c.duration for c in processed_clips)
        self.logger.info(
            f"Processed {len(processed_clips)} clips with total duration: {total_duration:.2f}s"
        )

        # Verify we reached the target duration
        if abs(total_duration - target_length) > 0.1:
            self.logger.warning(
                f"Target duration mismatch: target={target_length:.2f}s, actual={total_duration:.2f}s"
            )

        return processed_clips

    def create_final_video(self, video_generator=None):
        """Create final video with all components"""
        # video_generator parameter is kept for API compatibility but currently unused
        _ = video_generator  # Mark as used to avoid Pyright warning
        try:
            # Process media clips
            processed_clips = self.process_media_clips(self.media.media_files, self.args)
            if not processed_clips:
                raise ValueError("No valid media clips to process")

            self.logger.info(f"Processing {len(processed_clips)} media clips")

            # Concatenate clips with transitions
            if len(processed_clips) == 1:
                final_clip = processed_clips[0]
            else:
                # Add transitions between clips
                final_clips = []
                for i, clip in enumerate(processed_clips):
                    if i == 0:
                        # First clip, add directly
                        final_clips.append(clip)
                    else:
                        # Add transition with previous clip
                        transition = self.apply_transition(final_clips[-1], clip)
                        final_clips[-1] = transition  # Replace with transition

                final_clip = concatenate_videoclips(final_clips)

            # Add title
            if self.args.title:
                keep_title = getattr(self.args, "keep_title", False)
                final_clip = self.add_title(final_clip, self.args, use_full_duration=keep_title)

            # Add subtitles
            if hasattr(self, "subtitle_timestamps") and self.subtitle_timestamps:
                final_clip = self.add_timestamped_subtitles(final_clip)
            elif hasattr(self, "args") and hasattr(self.args, "subtitle") and self.args.subtitle:
                final_clip = self.add_subtitles(final_clip, self.args.subtitle, self.args)

            # Add audio if available
            if (
                hasattr(self, "audio_file")
                and self.audio_file
                and Path(self.audio_file).exists()
            ):
                try:
                    audio_clip = AudioFileClip(self.audio_file)
                    if audio_clip and final_clip and audio_clip.duration > final_clip.duration:
                        # Loop video to match audio duration
                        final_clip = final_clip.with_effects([vfx.TimeMirror()])  # Simple loop effect
                        # Alternative: use vfx.loop if available, otherwise create multiple copies
                    if final_clip and audio_clip:
                        # Handle with_audio method safely - ignore type checking for this line
                        final_clip = final_clip.with_audio(audio_clip)  # type: ignore
                    self.logger.info("Audio added to video")
                except Exception as e:
                    self.logger.error(f"Error adding audio: {e}")

            # Ensure output directory exists
            if self.paths and "project" in self.paths:
                output_dir = self.paths["project"] / "output"
                output_dir.mkdir(exist_ok=True)
            else:
                self.logger.error("Project paths not available")
                return None

            # Generate output filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            if 'output_dir' in locals():
                output_path = output_dir / f"video_{timestamp}.mp4"
            else:
                self.logger.error("Output directory not available")
                return None

            # Write final video with optimized settings
            self.logger.info(f"Creating final video: {output_path}")
            if final_clip:
                duration = final_clip.duration
                if duration is not None:
                    self.logger.info(f"Video duration: {duration:.2f}s")
                    self.logger.info("Starting video rendering... This may take a few minutes")

                    # Calculate optimal parameters based on video duration
                    preset = self._get_optimal_preset(duration)
                    crf = self._get_optimal_crf(duration)

                    # Set timeout based on video duration
                    timeout = max(300, int(duration * 10))  # 10x duration, minimum 5 minutes
                else:
                    self.logger.error("Video duration is None")
                    return None
            else:
                self.logger.error("No final video clip available")
                return None

            # Render with timeout
            result = self._render_with_timeout(
                final_clip, str(output_path), preset, crf, timeout
            )

            if result:
                self.logger.info(f"Final video created successfully: {output_path}")
                print(f"✅ Final video created: {output_path}")
                return str(output_path)
            else:
                self.logger.error("Video rendering timed out or failed")
                return None

        except Exception as e:
            self.logger.error(f"Error creating final video: {e}")
            return None

    def _get_optimal_preset(self, duration):
        """Get optimal ffmpeg preset based on video duration"""
        if duration < 30:
            return "veryfast"  # Fast encoding for short videos
        elif duration < 120:
            return "faster"  # Balanced for medium videos
        elif duration < 300:
            return "fast"  # Better quality for longer videos
        else:
            return "medium"  # Best quality for very long videos

    def _get_optimal_crf(self, duration):
        """Get optimal CRF value based on video duration"""
        if duration < 30:
            return 23  # Standard quality for short videos
        elif duration < 120:
            return 22  # Slightly better quality
        elif duration < 300:
            return 21  # Good quality for longer videos
        else:
            return 20  # Best quality for very long videos

    def _render_with_timeout(self, video_clip, output_path, preset, crf, timeout):
        """Render video with timeout to prevent hanging"""
        try:
            # Set timeout mechanism with signal (for Unix systems)
            import signal

            def timeout_handler(signum, frame):
                # signum and frame are required by signal.signal API but unused in this handler
                _ = signum, frame  # Mark as used to avoid Pyright warning
                raise TimeoutError("Video rendering timed out")

            # Set timeout
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)

            try:
                # Render the video
                video_clip.write_videofile(
                    output_path,
                    codec="libx264",
                    audio_codec="aac",
                    fps=self.video_settings.get("fps", 30),
                    preset=preset,
                    ffmpeg_params=["-crf", str(crf), "-movflags", "+faststart"],
                    threads=4,
                    verbose=True,
                    logger=None,
                )

                # Clear timeout
                signal.alarm(0)

                # Verify the output file exists and is valid
                if Path(output_path).exists() and Path(output_path).stat().st_size > 0:
                    self.logger.info(
                        f"Video rendered successfully: {Path(output_path).stat().st_size} bytes"
                    )
                    return True
                else:
                    self.logger.error("Output file is empty or doesn't exist")
                    return False

            except TimeoutError:
                self.logger.error(f"Video rendering timed out after {timeout} seconds")
                return False
            except Exception as e:
                self.logger.error(f"Error during video rendering: {e}")
                return False
            finally:
                # Clear timeout
                signal.alarm(0)

        except Exception as e:
            self.logger.error(f"Error in render with timeout: {e}")
            return False

