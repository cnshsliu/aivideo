#!/usr/bin/env python3
"""
Video Processing Module for AI Video Generator
Damn, this handles all the video stuff! Don't mess with it unless you know what you're doing!
"""

import os
import logging
import time
import signal
import threading
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union

from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    concatenate_videoclips, vfx, ImageClip, ColorClip, VideoClip
)
from moviepy.video.fx import resize, fadein, fadeout
import numpy as np
import random
from pathlib import Path

class VideoProcessor:
    """
    Video processing class - handles all the damn video operations
    """

    def __init__(self, config_manager, media_processor):
        self.config = config_manager
        self.media = media_processor
        self.logger = logging.getLogger(__name__)
        self.paths = config_manager.get_project_paths()
        self.video_settings = config_manager.get_video_settings()
        self.render_timeout = max(300, int(140 * 5))  # 5x video duration, minimum 5 minutes

        # Add target_width and target_height to video_settings if not present
        if 'target_width' not in self.video_settings:
            self.video_settings['target_width'] = 1080
        if 'target_height' not in self.video_settings:
            self.video_settings['target_height'] = 1920

    def add_title(self, clip: VideoClip, title_text: str = None, duration: float = 3.0,
                  use_full_duration: bool = False, keep_title: bool = False) -> VideoClip:
        """Add title to the beginning of video"""
        if not title_text:
            return clip

        title_settings = self.config.get_title_settings()
        font = self._get_chinese_compatible_font(title_settings['title_font'])
        position = title_settings['title_position'] / 100.0

        try:
            # Create title text clip
            title_clip = TextClip(
                title_text,
                fontsize=70,
                font=font,
                color='white',
                stroke_color='black',
                stroke_width=2,
                size=(clip.w, clip.h // 3),
                method='caption',
                align='center'
            )

            # Set position
            title_clip = title_clip.set_position(('center', position * clip.h))

            # Set duration
            if use_full_duration:
                title_clip = title_clip.set_duration(clip.duration)
            else:
                title_clip = title_clip.set_duration(min(duration, clip.duration))

            # Add fade effects
            title_clip = title_clip.fadein(0.5).fadeout(0.5)

            # Create title sequence
            title_sequence = CompositeVideoClip([clip, title_clip])

            # If not using full duration, concatenate with main clip
            if not use_full_duration:
                # Create a copy of the main clip for the title
                title_background = clip.subclip(0, title_clip.duration)
                title_sequence = CompositeVideoClip([title_background, title_clip])

                # Main content without the title portion
                main_content = clip.subclip(title_clip.duration)

                # Concatenate
                final_clip = concatenate_videoclips([title_sequence, main_content])
            else:
                final_clip = title_sequence

            return final_clip

        except Exception as e:
            self.logger.error(f"Error adding title: {e}")
            return clip

    def add_subtitles(self, clip: VideoClip, subtitle_text: str = None) -> VideoClip:
        """Add subtitles to video"""
        if not subtitle_text:
            return clip

        subtitle_settings = self.config.get_subtitle_settings()
        font = self._get_chinese_compatible_font(subtitle_settings['font'])
        position = subtitle_settings['position'] / 100.0

        try:
            # Create subtitle text clip
            subtitle_clip = TextClip(
                subtitle_text,
                fontsize=40,
                font=font,
                color='white',
                stroke_color='black',
                stroke_width=1,
                size=(clip.w * 0.9, clip.h // 4),
                method='caption',
                align='center'
            )

            # Set position
            subtitle_clip = subtitle_clip.set_position(('center', position * clip.h))

            # Set duration
            subtitle_clip = subtitle_clip.set_duration(clip.duration)

            # Composite with original clip
            final_clip = CompositeVideoClip([clip, subtitle_clip])

            return final_clip

        except Exception as e:
            self.logger.error(f"Error adding subtitle: {e}")
            return clip

    def add_timestamped_subtitles(self, video_clip: VideoClip, subtitles: List[Dict]) -> VideoClip:
        """Add subtitles with specific timestamps"""
        if not subtitles:
            return video_clip

        subtitle_settings = self.config.get_subtitle_settings()
        font = self._get_chinese_compatible_font(subtitle_settings['font'])
        position = subtitle_settings['position'] / 100.0

        try:
            # Create subtitle clips for each timestamp
            subtitle_clips = []

            for i, subtitle in enumerate(subtitles):
                # Validate subtitle structure
                if not isinstance(subtitle, dict):
                    self.logger.warning(f"Invalid subtitle at index {i}: not a dictionary")
                    continue

                # Extract text with validation
                text = subtitle.get('text', '')
                if not text or not text.strip():
                    self.logger.warning(f"Empty or missing text in subtitle at index {i}")
                    continue

                # Extract timestamps with validation
                start_time = subtitle.get('start', 0)
                end_time = subtitle.get('end', start_time + 3)

                # Validate timestamps
                if not isinstance(start_time, (int, float)) or start_time < 0:
                    self.logger.warning(f"Invalid start time in subtitle '{text}': {start_time}")
                    start_time = 0

                if not isinstance(end_time, (int, float)) or end_time <= start_time:
                    self.logger.warning(f"Invalid end time in subtitle '{text}': {end_time}")
                    end_time = start_time + 3

                duration = end_time - start_time
                if duration <= 0:
                    duration = 3  # Default duration
                    end_time = start_time + duration

                # Check if subtitle timing is within video duration
                if start_time >= video_clip.duration:
                    self.logger.warning(f"Subtitle '{text}' starts after video ends (start: {start_time}, video duration: {video_clip.duration})")
                    continue

                # Adjust end time if it exceeds video duration
                if end_time > video_clip.duration:
                    end_time = video_clip.duration
                    duration = end_time - start_time

                try:
                    # Create text clip
                    text_clip = TextClip(
                        text,
                        fontsize=40,
                        font=font,
                        color='white',
                        stroke_color='black',
                        stroke_width=1,
                        size=(video_clip.w * 0.9, video_clip.h // 4),
                        method='caption',
                        align='center'
                    )

                    # Set timing and position
                    text_clip = text_clip.set_start(start_time)
                    text_clip = text_clip.set_duration(duration)
                    text_clip = text_clip.set_position(('center', position * video_clip.h))

                    # Add fade effects
                    text_clip = text_clip.fadein(0.2).fadeout(0.2)

                    subtitle_clips.append(text_clip)
                    self.logger.debug(f"Added subtitle clip: '{text}' ({start_time:.2f}s - {end_time:.2f}s)")

                except Exception as e:
                    self.logger.warning(f"Error creating subtitle clip for '{text}': {e}")
                    continue

            # Composite all subtitles with video
            if subtitle_clips:
                self.logger.info(f"Adding {len(subtitle_clips)} subtitle clips to video")
                final_clip = CompositeVideoClip([video_clip] + subtitle_clips)
            else:
                self.logger.warning("No valid subtitle clips created")
                final_clip = video_clip

            return final_clip

        except Exception as e:
            self.logger.error(f"Error adding timestamped subtitles: {e}")
            return video_clip

    def _add_subtitles_fallback(self, video_clip: VideoClip) -> VideoClip:
        """Fallback method to add subtitles"""
        try:
            # Get a compatible font
            font = self._get_chinese_compatible_font()

            # Simple static subtitle in the middle
            subtitle_clip = TextClip(
                "AI Generated Video",
                fontsize=30,
                font=font,
                color='yellow',
                stroke_color='black',
                stroke_width=1
            )

            subtitle_clip = subtitle_clip.set_position(('center', 'center'))
            subtitle_clip = subtitle_clip.set_duration(video_clip.duration)

            return CompositeVideoClip([video_clip, subtitle_clip])

        except Exception as e:
            self.logger.error(f"Error in subtitle fallback: {e}")
            return video_clip

    def _get_chinese_compatible_font(self, default_font: str = 'Arial') -> str:
        """Get a font that supports Chinese characters"""
        chinese_fonts = [
            'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei',
            'SimHei', 'SimSun', 'Noto Sans CJK SC', 'Source Han Sans CN',
            'WenQuanYi Micro Hei', 'STHeiti', 'STXihei'
        ]

        # Try Chinese fonts first
        for font in chinese_fonts:
            try:
                # Test if font is available
                TextClip("测试", fontsize=12, font=font)
                self.logger.info(f"Using Chinese font: {font}")
                return font
            except:
                continue

        # Fall back to default font
        try:
            TextClip("test", fontsize=12, font=default_font)
            self.logger.info(f"Using default font: {default_font}")
            return default_font
        except:
            self.logger.warning("No suitable font found, using system default")
            return ""

    def apply_transition(self, clip1: VideoClip, clip2: VideoClip, duration: float = 0.5) -> VideoClip:
        """Apply transition between two clips"""
        try:
            # Validate input clips
            if not clip1 or not clip2:
                self.logger.warning("Invalid clips for transition, using simple concatenation")
                valid_clips = [clip for clip in [clip1, clip2] if clip]
                if valid_clips:
                    return concatenate_videoclips(valid_clips)
                else:
                    raise ValueError("No valid clips for transition")

            # Validate duration
            if duration <= 0:
                duration = 0.5

            # Ensure duration doesn't exceed clip lengths
            duration = min(duration, clip1.duration * 0.3, clip2.duration * 0.3)

            # Simple crossfade transition
            clip1_fade = clip1.fadeout(duration)
            clip2_fade = clip2.fadein(duration)

            # Create crossfade
            transition = CompositeVideoClip([
                clip1_fade,
                clip2_fade.set_start(clip1.duration - duration)
            ])

            return transition

        except Exception as e:
            self.logger.error(f"Error applying transition: {e}")
            # Fallback to simple concatenation with valid clips only
            valid_clips = [clip for clip in [clip1, clip2] if clip]
            if valid_clips:
                return concatenate_videoclips(valid_clips)
            else:
                raise ValueError("No valid clips for transition")

    def check_and_regenerate_aspect_ratio(self, video_file: Path) -> Tuple[int, int]:
        """Check and regenerate video with proper aspect ratio"""
        try:
            with VideoFileClip(str(video_file)) as clip:
                current_width, current_height = clip.w, clip.h

            # Check if aspect ratio is already correct
            target_width = self.video_settings['target_width']
            target_height = self.video_settings['target_height']
            target_aspect = target_width / target_height
            current_aspect = current_width / current_height

            if abs(current_aspect - target_aspect) < 0.01:
                self.logger.info(f"Video aspect ratio is already correct: {current_width}x{current_height}")
                return current_width, current_height

            # Determine which aspect ratio to use
            if target_aspect > 1:  # Landscape
                return self._regenerate_with_16_9_aspect_ratio(video_file, current_width, current_height)
            else:  # Portrait
                return self._regenerate_with_mobile_portrait_ratio(video_file, current_width, current_height)

        except Exception as e:
            self.logger.error(f"Error checking aspect ratio: {e}")
            return 1080, 1920  # Default mobile portrait

    def _regenerate_with_mobile_portrait_ratio(self, video_file: Path, current_width: int, current_height: int) -> Tuple[int, int]:
        """Regenerate video with mobile portrait aspect ratio"""
        target_width = self.video_settings['target_width']
        target_height = self.video_settings['target_height']

        self.logger.info(f"Regenerating video with mobile portrait ratio: {target_width}x{target_height}")

        try:
            # Load original video
            with VideoFileClip(str(video_file)) as clip:
                # Resize to mobile aspect ratio
                resized_clip = self._resize_to_mobile_aspect_ratio(clip, target_width, target_height)

                # Save with new aspect ratio
                output_path = video_file.parent / f"mobile_portrait_{video_file.name}"
                resized_clip.write_videofile(
                    str(output_path),
                    codec='libx264',
                    audio_codec='aac',
                    fps=clip.fps,
                    verbose=False,
                    logger=None
                )

                self.logger.info(f"Mobile portrait video created: {output_path}")

                # Replace original file
                video_file.unlink()
                output_path.rename(video_file)

                return target_width, target_height

        except Exception as e:
            self.logger.error(f"Error regenerating mobile portrait video: {e}")
            return current_width, current_height

    def _resize_to_mobile_aspect_ratio(self, clip: VideoClip, target_width: int = None, target_height: int = None) -> VideoClip:
        """Resize clip to mobile aspect ratio"""
        if target_width is None:
            target_width = self.video_settings['target_width']
        if target_height is None:
            target_height = self.video_settings['target_height']

        target_aspect = target_width / target_height
        current_aspect = clip.w / clip.h

        if current_aspect > target_aspect:
            # Video is wider than target - scale to match height, then crop width
            scale_factor = target_height / clip.h
            scaled_width = int(clip.w * scale_factor)
            scaled_height = target_height

            scaled_clip = clip.resize((scaled_width, scaled_height))
            crop_width = target_width
            crop_height = target_height
            left = (scaled_width - crop_width) // 2
            top = 0

        else:
            # Video is taller than target - scale to match width, then crop height
            scale_factor = target_width / clip.w
            scaled_width = target_width
            scaled_height = int(clip.h * scale_factor)

            scaled_clip = clip.resize((scaled_width, scaled_height))
            crop_width = target_width
            crop_height = target_height
            left = 0
            top = (scaled_height - crop_height) // 2

        # Perform the crop
        final_clip = scaled_clip.crop(left, top, left + crop_width, top + crop_height)

        self.logger.debug(f"Resized {clip.size} to {final_clip.size} for mobile aspect ratio")
        return final_clip

    def _regenerate_with_16_9_aspect_ratio(self, video_file: Path, current_width: int, current_height: int) -> Tuple[int, int]:
        """Regenerate video with 16:9 aspect ratio"""
        target_width = 1920
        target_height = 1080

        self.logger.info(f"Regenerating video with 16:9 ratio: {target_width}x{target_height}")

        try:
            # Load original video
            with VideoFileClip(str(video_file)) as clip:
                # Resize to 16:9 aspect ratio
                current_aspect = current_width / current_height
                target_aspect = 16 / 9

                if current_aspect > target_aspect:
                    # Video is wider than 16:9 - scale to match height, then crop width
                    scale_factor = target_height / clip.h
                    scaled_width = int(clip.w * scale_factor)
                    scaled_height = target_height

                    scaled_clip = clip.resize((scaled_width, scaled_height))
                    crop_width = target_width
                    crop_height = target_height
                    left = (scaled_width - crop_width) // 2
                    top = 0
                else:
                    # Video is taller than 16:9 - scale to match width, then crop height
                    scale_factor = target_width / clip.w
                    scaled_width = target_width
                    scaled_height = int(clip.h * scale_factor)

                    scaled_clip = clip.resize((scaled_width, scaled_height))
                    crop_width = target_width
                    crop_height = target_height
                    left = 0
                    top = (scaled_height - crop_height) // 2

                # Perform the crop
                final_clip = scaled_clip.crop(left, top, left + crop_width, top + crop_height)

                # Save with new aspect ratio
                output_path = video_file.parent / f"16_9_{video_file.name}"
                final_clip.write_videofile(
                    str(output_path),
                    codec='libx264',
                    audio_codec='aac',
                    fps=clip.fps,
                    verbose=False,
                    logger=None
                )

                self.logger.info(f"16:9 video created: {output_path}")

                # Replace original file
                video_file.unlink()
                output_path.rename(video_file)

                return target_width, target_height

        except Exception as e:
            self.logger.error(f"Error regenerating 16:9 video: {e}")
            return current_width, current_height

    def create_final_video(self, media_clips: List[VideoClip], audio_path: str = None,
                          title_text: str = None, subtitles: List[Dict] = None, keep_title: bool = False) -> Optional[str]:
        """Create final video with all components"""
        if not media_clips:
            self.logger.error("No media clips provided")
            return None

        try:
            # Concatenate media clips
            if len(media_clips) == 1:
                final_clip = media_clips[0]
            else:
                # Add transitions between clips
                final_clips = []
                for i, clip in enumerate(media_clips):
                    if i == 0:
                        # First clip, add directly
                        final_clips.append(clip)
                    else:
                        # Subsequent clips, add transition with previous clip
                        if final_clips and len(final_clips) > 0:
                            # Get the previous clip
                            prev_clip = final_clips[-1]

                            # Add transition between previous and current clip
                            transition = self.apply_transition(prev_clip, clip)

                            # Replace the previous clip with the transition
                            final_clips[-1] = transition
                        else:
                            # Fallback: just add the current clip
                            final_clips.append(clip)

                # Only concatenate if we have valid clips
                if final_clips and len(final_clips) > 0:
                    try:
                        # Filter out None clips that might have been added
                        valid_final_clips = [clip for clip in final_clips if clip is not None]
                        if valid_final_clips:
                            final_clip = concatenate_videoclips(valid_final_clips)
                        else:
                            # Fallback: use the first original media clip
                            if media_clips and media_clips[0] is not None:
                                final_clip = media_clips[0]
                            else:
                                raise ValueError("No valid media clips to concatenate")
                    except Exception as e:
                        self.logger.error(f"Error concatenating clips: {e}")
                        # Fallback: use the first original media clip
                        if media_clips and media_clips[0] is not None:
                            final_clip = media_clips[0]
                        else:
                            raise ValueError("No valid media clips to concatenate")
                else:
                    # Fallback: use the first clip if available
                    if media_clips and media_clips[0] is not None:
                        final_clip = media_clips[0]
                    else:
                        raise ValueError("No valid media clips to concatenate")

            # Add title
            if title_text:
                final_clip = self.add_title(final_clip, title_text, keep_title=keep_title)

            # Add audio
            if audio_path and Path(audio_path).exists():
                try:
                    audio_clip = AudioFileClip(audio_path)
                    # Expand video duration if audio is longer
                    if audio_clip.duration > final_clip.duration:
                        self.logger.info(f"Audio longer than video ({audio_clip.duration:.2f}s > {final_clip.duration:.2f}s), expanding video")
                        # Loop the video or add black screen
                        if final_clip.duration > 0:
                            loops = int(audio_clip.duration / final_clip.duration) + 1
                            final_clip = final_clip.loop(duration=audio_clip.duration)
                        else:
                            # Create black screen if no video content
                            final_clip = ColorClip(
                                size=(self.video_settings['target_width'], self.video_settings['target_height']),
                                color=(0, 0, 0),
                                duration=audio_clip.duration
                            )

                    final_clip = final_clip.set_audio(audio_clip)
                    self.logger.info("Audio added to video")
                except Exception as e:
                    self.logger.error(f"Error adding audio: {e}")

            # Add subtitles with additional validation
            if subtitles and isinstance(subtitles, list) and len(subtitles) > 0:
                try:
                    final_clip = self.add_timestamped_subtitles(final_clip, subtitles)
                except Exception as e:
                    self.logger.error(f"Error adding subtitles: {e}")
                    # Use fallback subtitle
                    final_clip = self._add_subtitles_fallback(final_clip)
            else:
                # Add fallback subtitle
                final_clip = self._add_subtitles_fallback(final_clip)

            # Ensure output directory exists
            output_dir = self.paths['project'] / "output"
            output_dir.mkdir(exist_ok=True)

            # Generate output filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"video_{timestamp}.mp4"

            # Write final video with timeout and optimized settings
            self.logger.info(f"Creating final video: {output_path}")
            self.logger.info(f"Video duration: {final_clip.duration:.2f}s")
            self.logger.info(f"Video size: {final_clip.size}")
            self.logger.info("Starting video rendering... This may take a few minutes")

            # Calculate optimal parameters based on video duration
            preset = self._get_optimal_preset(final_clip.duration)
            crf = self._get_optimal_crf(final_clip.duration)

            # Set timeout based on video duration
            timeout = max(300, int(final_clip.duration * 10))  # 10x duration, minimum 5 minutes
            self.logger.info(f"Timeout set to {timeout} seconds")

            # Render with timeout
            result = self._render_with_timeout(final_clip, str(output_path), preset, crf, timeout)

            if result:
                self.logger.info(f"Final video created successfully: {output_path}")
                return str(output_path)
            else:
                self.logger.error("Video rendering timed out or failed")
                return None

        except Exception as e:
            self.logger.error(f"Error creating final video: {e}")
            return None

    def _get_optimal_preset(self, duration: float) -> str:
        """Get optimal ffmpeg preset based on video duration"""
        if duration < 30:
            return 'veryfast'  # Fast encoding for short videos
        elif duration < 120:
            return 'faster'     # Balanced for medium videos
        elif duration < 300:
            return 'fast'       # Better quality for longer videos
        else:
            return 'medium'     # Best quality for very long videos

    def _get_optimal_crf(self, duration: float) -> int:
        """Get optimal CRF value based on video duration"""
        if duration < 30:
            return 23          # Standard quality for short videos
        elif duration < 120:
            return 22          # Slightly better quality
        elif duration < 300:
            return 21          # Good quality for longer videos
        else:
            return 20          # Best quality for very long videos

    def _render_with_timeout(self, video_clip, output_path: str, preset: str, crf: int, timeout: int) -> bool:
        """Render video with timeout to prevent hanging"""
        import multiprocessing as mp
        from functools import partial

        def render_worker(path, clip_data):
            """Worker function for rendering in separate process"""
            try:
                # Reconstruct the clip in the worker process
                # This is needed because MoviePy clips aren't picklable
                import sys
                from pathlib import Path
                from moviepy.editor import VideoFileClip, AudioFileClip

                # For simplicity, we'll just render a basic video
                # In a real implementation, you'd need to serialize the clip data

                # Create a simple test video
                from moviepy.editor import ColorClip, TextClip, CompositeVideoClip
                import numpy as np

                # Create a colored background
                background = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=clip_data['duration'])

                # Add some text
                font = self._get_chinese_compatible_font()
                text = TextClip("AI Generated Video", fontsize=40, color='white', size=(1080, 100), font=font)
                text = text.set_position('center').set_duration(clip_data['duration'])

                # Composite
                final_clip = CompositeVideoClip([background, text])

                # Add audio if available
                if clip_data.get('audio_path') and Path(clip_data['audio_path']).exists():
                    try:
                        audio = AudioFileClip(clip_data['audio_path'])
                        final_clip = final_clip.set_audio(audio)
                    except:
                        pass

                # Render the video
                final_clip.write_videofile(
                    path,
                    codec='libx264',
                    audio_codec='aac',
                    fps=30,
                    preset=preset,
                    ffmpeg_params=['-crf', str(crf), '-movflags', '+faststart'],
                    threads=4,
                    verbose=True,
                    logger=None
                )

                return True
            except Exception as e:
                print(f"Render worker error: {e}")
                return False

        try:
            # Prepare clip data for serialization
            clip_data = {
                'duration': video_clip.duration,
                'size': video_clip.size,
                'audio_path': None
            }

            # Extract audio path if available
            if hasattr(video_clip, 'audio') and video_clip.audio:
                # This is a simplification - in practice you'd need to save the audio
                pass

            self.logger.info(f"Starting video render with timeout: {timeout}s")

            # Use timeout mechanism with signal (for Unix systems)
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError("Video rendering timed out")

            # Set timeout
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)

            try:
                # Render the video directly (simplified approach)
                video_clip.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    fps=self.video_settings['fps'],
                    preset=preset,
                    ffmpeg_params=['-crf', str(crf), '-movflags', '+faststart'],
                    threads=4,
                    verbose=True,
                    logger=None
                )

                # Clear timeout
                signal.alarm(0)

                # Verify the output file exists and is valid
                if Path(output_path).exists() and Path(output_path).stat().st_size > 0:
                    self.logger.info(f"Video rendered successfully: {Path(output_path).stat().st_size} bytes")
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

    def get_video_duration(self, video_path: str) -> float:
        """Get video duration"""
        try:
            with VideoFileClip(video_path) as clip:
                return clip.duration
        except Exception as e:
            self.logger.error(f"Error getting video duration: {e}")
            return 0

    def validate_video_file(self, video_path: str) -> bool:
        """Validate video file"""
        if not video_path or not Path(video_path).exists():
            return False

        try:
            with VideoFileClip(video_path) as clip:
                return clip.duration > 0 and clip.w > 0 and clip.h > 0
        except Exception as e:
            self.logger.error(f"Error validating video file: {e}")
            return False

    def _safe_load_video_clip(self, file_path: Path, max_duration_check: float = 10.0) -> VideoClip:
        """Safely load a video clip with error handling for corrupted files"""
        try:
            self.logger.debug(f"Loading video clip: {file_path}")

            # Check file exists and is readable
            if not file_path.exists():
                self.logger.error(f"Video file does not exist: {file_path}")
                return None

            # Check file size
            if file_path.stat().st_size == 0:
                self.logger.error(f"Video file is empty: {file_path}")
                return None

            # Try to load the clip
            clip = VideoFileClip(str(file_path))

            # Check if clip has valid properties
            if clip is None:
                self.logger.error(f"Failed to load video clip: {file_path}")
                return None

            # Check duration
            if not hasattr(clip, 'duration') or clip.duration <= 0:
                self.logger.error(f"Video clip has invalid duration: {file_path}")
                clip.close()
                return None

            # Check dimensions
            if not hasattr(clip, 'w') or not hasattr(clip, 'h') or clip.w <= 0 or clip.h <= 0:
                self.logger.error(f"Video clip has invalid dimensions: {file_path}")
                clip.close()
                return None

            # Check if duration is reasonable (not too long)
            if max_duration_check and clip.duration > max_duration_check:
                self.logger.warning(f"Video clip duration {clip.duration}s exceeds check duration {max_duration_check}s: {file_path}")
                clip.close()
                return None

            # Try to get a frame to test if the video is corrupted
            try:
                test_frame = clip.get_frame(0)
                if test_frame is None or test_frame.size == 0:
                    self.logger.error(f"Video clip failed frame test: {file_path}")
                    clip.close()
                    return None
            except Exception as frame_error:
                self.logger.error(f"Video clip frame test failed: {file_path}, error: {frame_error}")
                clip.close()
                return None

            self.logger.debug(f"Successfully loaded video clip: {file_path} ({clip.duration:.2f}s, {clip.w}x{clip.h})")
            return clip

        except Exception as e:
            self.logger.error(f"Error loading video clip {file_path}: {e}")
            return None

    def _safe_concatenate_clips(self, clips: List[VideoClip], method: str = "compose") -> VideoClip:
        """Safely concatenate clips with robust error handling"""
        if not clips:
            self.logger.error("No clips to concatenate")
            return None

        # Filter out None clips
        valid_clips = [clip for clip in clips if clip is not None]
        if len(valid_clips) != len(clips):
            self.logger.warning(f"Filtered out {len(clips) - len(valid_clips)} None clips")

        if not valid_clips:
            self.logger.error("No valid clips to concatenate")
            return None

        if len(valid_clips) == 1:
            self.logger.debug("Single clip, no concatenation needed")
            return valid_clips[0]

        try:
            # Log clip information
            total_duration = sum(clip.duration for clip in valid_clips)
            self.logger.debug(f"Concatenating {len(valid_clips)} clips, total duration: {total_duration:.2f}s")

            # Try concatenation
            if method == "compose":
                result = concatenate_videoclips(valid_clips, method="compose")
            else:
                result = concatenate_videoclips(valid_clips, method=method)

            # Verify result
            if result is None:
                self.logger.error("Concatenation returned None")
                return None

            if not hasattr(result, 'duration') or result.duration <= 0:
                self.logger.error("Concatenated clip has invalid duration")
                return None

            self.logger.debug(f"Successfully concatenated clips: {result.duration:.2f}s")
            return result

        except Exception as e:
            self.logger.error(f"Error concatenating clips: {e}")
            return None

    def _process_with_original_length(self, clips: List[Path], args: object) -> List[VideoClip]:
        """Process clips keeping their original length"""
        processed_clips = []
        target_length = getattr(args, 'length', None)

        self.logger.info(f"Starting _process_with_original_length with target_length: {target_length}")

        # First pass: process all clips normally
        for i, clip_path in enumerate(clips):
            try:
                if clip_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}:
                    # Convert image to video clip
                    clip = ImageClip(str(clip_path)).set_duration(3.0)
                    # Resize image to mobile aspect ratio
                    clip = self._resize_to_mobile_aspect_ratio(clip)
                    self.logger.debug(f"Converted and resized image to clip: {clip_path} (3.0s)")
                else:
                    # Video clip with safe loading for corrupted files
                    clip = self._safe_load_video_clip(clip_path)
                    if clip is None:
                        self.logger.warning(f"Skipping corrupted video clip: {clip_path}")
                        continue
                    # Resize video clip to fit mobile aspect ratio (remove black borders)
                    clip = self._resize_to_mobile_aspect_ratio(clip)
                    self.logger.debug(f"Loaded and resized video clip: {clip_path} ({clip.duration:.2f}s -> {clip.w}x{clip.h})")

                # Make clip silent if requested
                if getattr(args, 'clip_silent', False):
                    clip = clip.without_audio()

                processed_clips.append(clip)

                # Stop if we've exceeded target length
                total_duration = sum(c.duration for c in processed_clips)
                if target_length and total_duration >= target_length:
                    self.logger.info(f"Reached target length {target_length}s at clip {i+1}, stopping clip processing")
                    break

            except Exception as e:
                self.logger.error(f"Failed to process {clip_path}: {e}")
                continue

        total_duration = sum(c.duration for c in processed_clips)
        self.logger.info(f"After initial processing: {len(processed_clips)} clips with total duration: {total_duration:.2f}s")

        # If we have a target length and haven't reached it, extend by repeating clips
        if target_length and total_duration < target_length and processed_clips:
            needed_extension = target_length - total_duration
            self.logger.info(f"Need to extend video by {needed_extension:.2f}s to reach target of {target_length}s")

            remaining_duration = needed_extension
            clip_index = 0
            original_clip_count = len(processed_clips)

            while remaining_duration > 0.01 and processed_clips:  # Use small threshold to avoid infinite loops
                # Repeat clips to fill the remaining duration
                clip_to_repeat = processed_clips[clip_index % original_clip_count]

                if clip_to_repeat.duration <= remaining_duration + 0.01:  # Small tolerance
                    # Use the entire clip
                    repeated_clip = clip_to_repeat.copy()
                    processed_clips.append(repeated_clip)
                    remaining_duration -= clip_to_repeat.duration
                    self.logger.debug(f"Added full clip {clip_index % original_clip_count + 1} ({clip_to_repeat.duration:.2f}s), remaining: {remaining_duration:.2f}s")
                else:
                    # Use part of the clip
                    partial_clip = clip_to_repeat.subclip(0, remaining_duration)
                    processed_clips.append(partial_clip)
                    self.logger.debug(f"Added partial clip ({remaining_duration:.2f}s) from clip {clip_index % original_clip_count + 1}")
                    remaining_duration = 0

                clip_index += 1

                # Safety check to prevent infinite loops
                if clip_index > original_clip_count * 10:  # Max 10 full cycles
                    self.logger.warning("Reached safety limit for clip repetition, stopping extension")
                    break

        total_duration = sum(c.duration for c in processed_clips)
        self.logger.info(f"Final _process_with_original_length: {len(processed_clips)} clips with total duration: {total_duration:.2f}s")

        if target_length:
            self.logger.info(f"Target vs Actual: {target_length:.2f}s vs {total_duration:.2f}s (diff: {abs(target_length - total_duration):.2f}s)")

        return processed_clips

    def _process_with_target_length(self, clips: List[Path], args: object) -> List[VideoClip]:
        """Process clips to fit target length"""
        target_length = getattr(args, 'length', None)
        if not target_length:
            raise ValueError("Target length must be specified when not keeping clip length")

        self.logger.info(f"Processing clips to fit target length: {target_length}s")
        clip_duration = target_length / len(clips)
        self.logger.info(f"Each clip will be: {clip_duration:.2f}s")

        processed_clips = []

        for clip_path in clips:
            try:
                if clip_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}:
                    # Convert image to video clip
                    clip = ImageClip(str(clip_path)).set_duration(clip_duration)
                    # Resize image to mobile aspect ratio
                    clip = self._resize_to_mobile_aspect_ratio(clip)
                    self.logger.debug(f"Created and resized image clip: {clip_path} ({clip_duration:.2f}s -> {clip.w}x{clip.h})")
                else:
                    # Video clip - process to exact duration with safe loading
                    full_clip = self._safe_load_video_clip(clip_path)
                    if full_clip is None:
                        self.logger.warning(f"Skipping corrupted video clip: {clip_path}")
                        continue

                    # Resize the full clip to mobile aspect ratio before processing
                    full_clip = self._resize_to_mobile_aspect_ratio(full_clip)
                    self.logger.debug(f"Resized video clip to mobile aspect ratio: {clip_path} ({full_clip.w}x{full_clip.h})")

                    if full_clip.duration >= clip_duration:
                        # Trim to exact duration
                        start_time = random.uniform(0, full_clip.duration - clip_duration)
                        clip = full_clip.subclip(start_time, start_time + clip_duration)
                        self.logger.debug(f"Trimmed video clip: {clip_path} ({clip_duration:.2f}s from {start_time:.2f}s)")
                    else:
                        # Clip is shorter than target duration - need to extend it
                        remaining_duration = clip_duration - full_clip.duration
                        extended_clips = [full_clip]

                        # Safety check for invalid remaining duration
                        if remaining_duration <= 0:
                            self.logger.warning(f"Invalid remaining duration: {remaining_duration:.2f}s for {clip_path}")
                            clip = full_clip
                        else:
                            # Keep repeating the clip to fill the remaining duration
                            self.logger.info(f"Extending clip {clip_path} from {full_clip.duration:.2f}s to {clip_duration:.2f}s")

                            # Maximum repetitions to prevent infinite loops - be more conservative
                            max_repetitions = int(clip_duration / full_clip.duration) + 1
                            if max_repetitions > 20:  # Hard limit to prevent excessive repetitions
                                max_repetitions = 20
                            repetition_count = 0

                            while remaining_duration > 0.01 and repetition_count < max_repetitions:
                                repetition_count += 1

                                if full_clip.duration <= remaining_duration + 0.01:  # Add small tolerance
                                    # Use full clip again
                                    try:
                                        repeated_clip = full_clip.copy()
                                        # Verify the copied clip has valid duration
                                        if hasattr(repeated_clip, 'duration') and repeated_clip.duration > 0:
                                            extended_clips.append(repeated_clip)
                                            remaining_duration -= repeated_clip.duration
                                            self.logger.debug(f"Repeated full clip {clip_path} ({repetition_count}), remaining: {remaining_duration:.2f}s")
                                        else:
                                            self.logger.warning(f"Invalid copied clip duration for {clip_path}")
                                            break
                                    except Exception as copy_error:
                                        self.logger.error(f"Failed to copy clip {clip_path}: {copy_error}")
                                        break
                                else:
                                    # Use partial clip - add safety checks
                                    try:
                                        # Ensure we don't exceed the clip duration
                                        safe_end_time = min(remaining_duration, full_clip.duration)
                                        if safe_end_time > 0.01:  # Minimum duration check
                                            partial_clip = full_clip.subclip(0, safe_end_time)
                                            # Verify the partial clip is valid
                                            if hasattr(partial_clip, 'duration') and partial_clip.duration > 0:
                                                extended_clips.append(partial_clip)
                                                self.logger.debug(f"Added partial clip ({safe_end_time:.2f}s) from {clip_path}")
                                            else:
                                                self.logger.warning(f"Invalid partial clip created from {clip_path}")
                                                # Use full clip as fallback
                                                extended_clips.append(full_clip.copy())
                                                remaining_duration -= full_clip.duration
                                        else:
                                            self.logger.warning(f"Invalid safe_end_time: {safe_end_time:.2f}s")
                                            break
                                    except Exception as subclip_error:
                                        self.logger.error(f"Failed to create subclip from {clip_path}: {subclip_error}")
                                        # Use full clip as fallback
                                        try:
                                            extended_clips.append(full_clip.copy())
                                            remaining_duration -= full_clip.duration
                                        except Exception as fallback_error:
                                            self.logger.error(f"Fallback also failed for {clip_path}: {fallback_error}")
                                            break

                                remaining_duration = max(0, remaining_duration)  # Ensure non-negative

                            # Concatenate all extended clips with error handling
                            if len(extended_clips) > 1:
                                try:
                                    # Verify all clips have valid durations before concatenation
                                    valid_clips = []
                                    for i, extended_clip in enumerate(extended_clips):
                                        if hasattr(extended_clip, 'duration') and extended_clip.duration > 0:
                                            valid_clips.append(extended_clip)
                                        else:
                                            self.logger.warning(f"Skipping invalid extended clip {i} from {clip_path}")

                                    if len(valid_clips) > 0:
                                        clip = self._safe_concatenate_clips(valid_clips, method="compose")
                                        self.logger.info(f"Successfully extended video clip: {clip_path} (original: {full_clip.duration:.2f}s, extended: {clip.duration:.2f}s)")
                                    else:
                                        self.logger.error(f"No valid clips to concatenate for {clip_path}")
                                        clip = full_clip  # Fallback to original

                                except Exception as concat_error:
                                    self.logger.error(f"Failed to concatenate extended clips for {clip_path}: {concat_error}")
                                    # Fallback to original clip
                                    clip = full_clip
                            else:
                                clip = extended_clips[0] if extended_clips else full_clip

                # Make clip silent if requested
                if getattr(args, 'clip_silent', False):
                    clip = clip.without_audio()

                processed_clips.append(clip)

            except Exception as e:
                self.logger.error(f"Failed to process {clip_path}: {e}")
                continue

        total_duration = sum(c.duration for c in processed_clips)
        self.logger.info(f"Processed {len(processed_clips)} clips with total duration: {total_duration:.2f}s")

        # Verify we reached the target duration
        if abs(total_duration - target_length) > 0.1:
            self.logger.warning(f"Target duration mismatch: target={target_length:.2f}s, actual={total_duration:.2f}s")

        return processed_clips

    def process_media_clips(self, clips: List[Path], args: object) -> List[VideoClip]:
        """Process media clips based on target length setting"""
        if getattr(args, 'keep_clip_length', False):
            return self._process_with_original_length(clips, args)
        else:
            return self._process_with_target_length(clips, args)