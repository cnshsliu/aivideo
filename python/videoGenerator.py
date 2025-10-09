import os
import random
import time
import subprocess
from typing import TypeVar
import numpy as np
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
    vfx,
    ImageClip,
)
from moviepy.video.fx import FadeIn, FadeOut


# Import configuration module
from title_processor import TitleProcessor
from subtitle_processor import SubtitleProcessor
from background_music import BackgroundMusicProcessor
from audio_generator import AudioGenerator
from config_module import Config

# Import LLM module
from llm_module import LLMManager

# Import utility functions
from utils_module import (
    contains_chinese,
    split_long_subtitle_text,
    calculate_safe_max_chars,
    get_chinese_compatible_font,
)

# Type annotations for MoviePy objects
ClipType = TypeVar("ClipType")
VideoClipType = TypeVar("VideoClipType")
TextClipType = TypeVar("TextClipType")
ImageClipType = TypeVar("ImageClipType")
CompositeVideoClipType = TypeVar("CompositeVideoClipType")
AudioClipType = TypeVar("AudioClipType")


class VideoGenerator:
    """
    Main video generator class - handles the whole damn process
    Don't even think about messing with the state unless you know what you're doing!
    """

    def __init__(self, args):
        self.config = Config(args)
        self.args = args
        self.project_folder = self.config.project_folder
        self.media_folder = self.project_folder / "media"
        self.prompt_folder = self.project_folder / "prompt"
        self.subtitle_folder = self.project_folder / "subtitle"
        self.logger = self.config.logger
        self.llm_manager = LLMManager(self.config)
        # Initialize subtitle processor
        self.title_processor = TitleProcessor(self.logger)
        self.subtitle_processor = SubtitleProcessor(self, self.logger)
        self.background_music_processor = BackgroundMusicProcessor(self.logger, args)
        self.audioGenerator = AudioGenerator(self.logger)
        self.subtitle_timestamps = []

        # Media files list
        self.media_files = []
        self.start_file = None
        self.closing_file = None

        # Generated content
        self.subtitles = []
        self.voice_subtitles = []  # For TTS (with punctuation)
        self.display_subtitles = []  # For video display (cleaned)
        self.display_to_voice_mapping = []  # Maps display subtitle index to voice subtitle index
        self.audio_file = None

    def scan_media_files(self):
        """Scan media folder and identify special files"""
        # Find all media files (videos and images)
        media_extensions = {
            ".mp4",
            ".avi",
            ".mov",
            ".mkv",
            ".wmv",
            ".flv",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".tiff",
        }

        all_files = []
        for file_path in self.media_folder.iterdir():
            if file_path.suffix.lower() in media_extensions:
                # Check for special files
                if file_path.stem.lower().startswith("start"):
                    self.logger.info(f"Found start file: {file_path.name}")
                    if not self.start_file or file_path.name < self.start_file.name:
                        self.start_file = file_path
                elif file_path.stem.lower().startswith(("closing", "close")):
                    if not self.closing_file or file_path.name < self.closing_file.name:
                        self.closing_file = file_path
                else:
                    all_files.append(file_path)

        self.logger.info(f"Finaly start file {self.start_file}")

        # Sort media files according to the specified method
        if self.args.sort == "alphnum":
            all_files.sort(key=lambda x: x.name.lower())
        elif self.args.sort == "random":
            random.shuffle(all_files)

        self.media_files = all_files
        print(f"Found {len(self.media_files)} media files")
        if self.start_file:
            print(f"Found start file: {self.start_file}")
        if self.closing_file:
            print(f"Found closing file: {self.closing_file}")

    def process_media_clips(self):
        """Process media clips according to specifications"""
        if not self.media_files:
            raise ValueError("No media files found")

        self.logger.info(
            f"Processing media clips with args.length: {getattr(self.args, 'length', 'None')}"
        )
        self.logger.info(f"Available media files: {len(self.media_files)}")

        # Determine how many clips to use
        clip_num = len(self.media_files)
        if self.args.clip_num and self.args.clip_num > 0:
            clip_num = min(self.args.clip_num, len(self.media_files))

        selected_clips = self.media_files[:clip_num]
        self.logger.info(f"Selected {len(selected_clips)} clips for processing")

        if self.args.keep_clip_length:
            # Keep original clip lengths
            self.logger.info("Using keep_clip_length mode")
            return self._process_with_original_length(selected_clips)
        else:
            # Check if we have a target length
            target_length = getattr(self.args, "length", None)
            self.logger.info(f"Target length check: {target_length}")
            if target_length:
                # Cut clips to fit target length
                self.logger.info("Using target length mode")
                return self._process_with_target_length(selected_clips)
            else:
                # No target length specified - keep original lengths
                self.logger.info(
                    "No target length specified, keeping original clip lengths"
                )
                return self._process_with_original_length(selected_clips)

    def _resize_to_mobile_aspect_ratio(self, clip):
        """Resize video clip to mobile portrait 9:16 aspect ratio with center scaling"""
        try:
            # Test the original clip first
            try:
                test_frame = clip.get_frame(0.0)
                if test_frame is None or not isinstance(test_frame, np.ndarray):
                    raise ValueError("Original clip cannot be read")
            except Exception as frame_error:
                self.logger.error(f"Original clip frame read failed: {frame_error}")
                return clip

            # Target mobile portrait resolution (9:16) - width:height = 9:16
            target_width = 1080  # Standard mobile portrait width
            target_height = 1920  # Standard mobile portrait height

            # Get original clip dimensions
            original_width = clip.w
            original_height = clip.h

            self.logger.info(f"Original dimensions: {original_width}x{original_height}")

            # Check if clip is smaller than target mobile screen
            is_smaller = (original_width < target_width) or (
                original_height < target_height
            )

            if is_smaller:
                # Clip is smaller than screen - center and scale up until smaller dimension covers screen
                self.logger.info(
                    "Clip is smaller than mobile screen, centering and scaling up..."
                )

                # Calculate scale factor needed to cover the screen
                # We want the smaller dimension to exactly match the target
                scale_width = target_width / original_width
                scale_height = target_height / original_height

                # Choose the larger scale factor to ensure full coverage
                scale_factor = max(scale_width, scale_height)

                # Calculate new dimensions after scaling
                scaled_width = int(original_width * scale_factor)
                scaled_height = int(original_height * scale_factor)

                self.logger.info(
                    f">>>Scaling up by factor {scale_factor:.2f} to {scaled_width}x{scaled_height}"
                )

                # Resize the clip
                scaled_clip = clip.with_effects(
                    [vfx.Resize(new_size=(scaled_width, scaled_height))]
                )

                # Crop from center to target dimensions
                x_center = scaled_width // 2
                y_center = scaled_height // 2
                x1 = max(0, x_center - target_width // 2)
                x2 = min(scaled_width, x_center + target_width // 2)
                y1 = max(0, y_center - target_height // 2)
                y2 = min(scaled_height, y_center + target_height // 2)

                final_clip = scaled_clip.cropped(x1=x1, y1=y1, x2=x2, y2=y2)

                self.logger.info(
                    f"Cropped to mobile portrait: {target_width}x{target_height}"
                )

                # Clean up
                scaled_clip.close()

                return final_clip

            else:
                # Clip is larger than or equal to screen - crop to 9:16 aspect ratio
                self.logger.info(
                    "Clip is larger than mobile screen, cropping to 9:16 aspect ratio..."
                )

                # Target aspect ratio for mobile portrait: 9:16 (width:height)
                target_aspect = 9 / 16  # 0.5625
                original_aspect = original_width / original_height

                if original_aspect > target_aspect:
                    # Original is wider than target - crop width
                    new_width = int(original_height * target_aspect)
                    new_height = original_height
                    x_center = original_width // 2
                    x1 = max(0, x_center - new_width // 2)
                    x2 = min(original_width, x_center + new_width // 2)
                    y1 = 0
                    y2 = original_height
                else:
                    # Original is taller than target - crop height
                    new_width = original_width
                    new_height = int(original_width / target_aspect)
                    y_center = original_height // 2
                    y1 = max(0, y_center - new_height // 2)
                    y2 = min(original_height, y_center + new_height // 2)
                    x1 = 0
                    x2 = original_width

                # Crop the clip to the target aspect ratio
                cropped_clip = clip.cropped(x1=x1, y1=y1, x2=x2, y2=y2)

                # Resize to target mobile resolution
                final_clip = cropped_clip.with_effects(
                    [vfx.Resize(new_size=(target_width, target_height))]
                )

                self.logger.info(
                    f"Cropped and resized to mobile portrait: {target_width}x{target_height}"
                )

                # Clean up
                cropped_clip.close()

                return final_clip

        except Exception as e:
            self.logger.error(f"Error in _resize_to_mobile_aspect_ratio: {e}")
            return clip

    def _safe_load_video_clip(self, file_path, max_duration_check=10.0):
        """Safely load a video clip with error handling for corrupted files"""
        try:
            # First try to get basic file info
            if not file_path.exists():
                self.logger.warning(f"File does not exist: {file_path}")
                return None

            # Try to load with a quick duration check first
            test_clip = VideoFileClip(str(file_path), audio=True)

            # Check if duration is valid
            if (
                not hasattr(test_clip, "duration")
                or test_clip.duration is None
                or test_clip.duration <= 0
            ):
                self.logger.warning(
                    f"Invalid duration for {file_path}: {getattr(test_clip, 'duration', 'unknown')}"
                )
                test_clip.close()
                return None

            # Check if file is too long (might be corrupted)
            if test_clip.duration > 3600:  # More than 1 hour
                self.logger.warning(
                    f"File seems too long ({test_clip.duration:.2f}s), might be corrupted: {file_path}"
                )
                test_clip.close()
                return None

            # Quick check of first few frames
            if test_clip and test_clip.duration > max_duration_check:
                # Try to read a frame from the beginning
                try:
                    subclip = test_clip.subclipped(0, min(1.0, test_clip.duration))
                    if subclip:
                        subclip.close()
                except Exception as frame_error:
                    self.logger.warning(
                        f"Failed to read initial frames from {file_path}: {frame_error}"
                    )
                    if test_clip:
                        test_clip.close()
                    return None

                # Try to read a frame from near the end to detect corruption
                try:
                    end_check_start = max(0, test_clip.duration - max_duration_check)
                    end_subclip = test_clip.subclipped(
                        end_check_start, test_clip.duration
                    )
                    if end_subclip:
                        end_subclip.close()
                except Exception as frame_error:
                    # Don't fail completely for end-frame issues - many files have this problem
                    self.logger.info(
                        f"Minor corruption detected at end of {file_path} (ignoring): {frame_error}"
                    )
                    # Continue with the clip - it's still usable

            # If all checks pass, return the clip without resizing for now
            # TEMPORARY: Disabled mobile aspect ratio resizing due to frame read issues
            final_clip = test_clip
            self.logger.info(
                f"Successfully loaded video clip: {file_path} ({final_clip.duration:.2f}s) [resizing disabled]"
            )
            return final_clip

        except Exception as e:
            self.logger.warning(f"Failed to load video clip {file_path}: {e}")
            return None

    def _safe_concatenate_clips(self, clips, method="compose"):
        """Safely concatenate clips with robust error handling"""
        if len(clips) == 0:
            raise ValueError("No clips to concatenate")

        if len(clips) == 1:
            return clips[0]

        self.logger.info(f"Concatenating {len(clips)} clips with method: {method}")

        # Filter out any invalid clips
        valid_clips = []
        for i, clip in enumerate(clips):
            # First check basic properties
            if (
                not hasattr(clip, "duration")
                or clip.duration is None
                or clip.duration <= 0
            ):
                self.logger.warning(
                    f"Skipping invalid clip {i}: duration={getattr(clip, 'duration', 'unknown')}"
                )
                continue

            # Test if the clip can actually be read
            try:
                # Try to get frame at the beginning of the clip
                test_frame = clip.get_frame(0.0)
                self.logger.info(
                    f"Clip {i}: get_frame returned type: {type(test_frame)}"
                )

                if test_frame is None:
                    self.logger.warning(f"Skipping clip {i}: frame is None")
                    continue

                if not isinstance(test_frame, np.ndarray):
                    self.logger.warning(
                        f"Skipping clip {i}: frame is not numpy array, got {type(test_frame)} with value: {test_frame}"
                    )
                    continue

                # Additional validation - check if frame has proper dimensions
                if len(test_frame.shape) != 3 or test_frame.shape[2] not in [3, 4]:
                    self.logger.warning(
                        f"Skipping clip {i}: invalid frame format {test_frame.shape}"
                    )
                    continue

            except Exception as frame_error:
                self.logger.warning(
                    f"Skipping clip {i}: frame read error - {frame_error}"
                )
                continue

            # If all checks pass, add to valid clips
            valid_clips.append(clip)
            self.logger.debug(f"Clip {i} is valid: duration={clip.duration:.2f}s")

        if len(valid_clips) == 0:
            raise ValueError("No valid clips available for concatenation")

        if len(valid_clips) == 1:
            self.logger.info("Only one valid clip, no concatenation needed")
            return valid_clips[0]

        # Try different concatenation methods
        try:
            # Method 1: Standard concatenate_videoclips
            self.logger.info("Attempting standard concatenate_videoclips...")
            result = concatenate_videoclips(valid_clips, method=method)

            # Verify the result can be read
            if result is None:
                raise ValueError("concatenate_videoclips returned None")

            try:
                test_frame = result.get_frame(0.0)
                if test_frame is None or not isinstance(test_frame, np.ndarray):
                    raise ValueError("Cannot read frames from concatenated clip")
            except Exception as frame_error:
                raise ValueError(
                    f"Cannot read frames from concatenated clip: {frame_error}"
                )

            self.logger.info(f"Successfully concatenated {len(valid_clips)} clips")
            return result
        except Exception as e:
            self.logger.warning(f"Standard concatenation failed: {e}")

        # Method 2: Try with different method
        try:
            self.logger.info("Attempting concatenation with chain method...")
            result = concatenate_videoclips(valid_clips, method="chain")
            self.logger.info(
                f"Successfully concatenated {len(valid_clips)} clips with chain method"
            )
            return result
        except Exception as e:
            self.logger.warning(f"Chain concatenation failed: {e}")

        # Method 3: Create individual video files and use ffmpeg directly as last resort
        try:
            self.logger.info("Attempting manual concatenation approach...")
            # For now, just return the first valid clip as fallback
            self.logger.warning(
                "Concatenation failed, using first valid clip as fallback"
            )
            return valid_clips[0]
        except Exception as e:
            self.logger.error(f"Manual concatenation also failed: {e}")
            raise ValueError(
                f"Failed to concatenate clips after multiple attempts: {e}"
            )

    def _process_with_original_length(self, clips):
        """Process clips keeping their original length"""
        processed_clips = []
        target_length = getattr(self.args, "length", None)

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
                print(f"Damn, failed to process {clip_path}: {e}")
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
                    partial_clip = clip_to_repeat.subclipped(0, remaining_duration)
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

    def _process_with_target_length(self, clips):
        """Process clips to fit target length"""
        target_length = getattr(self.args, "length", None)
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
                        clip = full_clip.subclipped(
                            start_time, start_time + clip_duration
                        )
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
                                            partial_clip = full_clip.subclipped(
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
                clip = clip.without_audio()

                processed_clips.append(clip)

            except Exception as e:
                self.logger.error(f"Failed to process {clip_path}: {e}")
                print(f"Failed to process {clip_path}: {e}")
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

    def add_timestamped_subtitles(self, video_clip):
        """Add all subtitles with their specific timestamps to the video"""
        if not hasattr(self, "subtitle_timestamps") or not self.subtitle_timestamps:
            self.logger.warning(
                "No timestamped subtitles available, using fallback method"
            )
            # Fallback to old method if timestamps not available
            return video_clip

        try:
            self.logger.info(
                f"Adding {len(self.subtitle_timestamps)} timestamped subtitles to video"
            )

            # Get subtitle styling parameters
            font_size = getattr(self.args, "subtitle_font_size", 48)
            if font_size is None:
                font_size = 48
            subtitle_font = getattr(self.args, "subtitle_font", "Arial") or "Arial"
            subtitle_position = getattr(self.args, "subtitle_position", 80)
            if subtitle_position is None:
                subtitle_position = 80

            # Check if we need Chinese font support
            needs_chinese_font = any(
                contains_chinese(sub["text"]) for sub in self.subtitle_timestamps
            )
            if needs_chinese_font:
                self.logger.info(
                    "Chinese text detected in subtitles, using compatible font"
                )
                subtitle_font = get_chinese_compatible_font(subtitle_font)
                if subtitle_font is None:
                    self.logger.error("No compatible font found for Chinese text")
                    return video_clip

            self.logger.info(f"Creating subtitles with font: {subtitle_font}")

            # Create subtitle clips with proper timing
            subtitle_clips = []
            video_duration = video_clip.duration

            for subtitle_info in self.subtitle_timestamps:
                text = subtitle_info["text"]
                start_time = subtitle_info["start_time"]
                end_time = subtitle_info["end_time"]

                # Ensure subtitle timing is within video bounds
                if start_time >= video_duration:
                    continue  # Skip subtitles that start after video ends
                if end_time > video_duration:
                    end_time = (
                        video_duration  # Truncate subtitles that extend beyond video
                    )

                # Calculate subtitle duration
                subtitle_duration = end_time - start_time
                if subtitle_duration <= 0:
                    continue  # Skip invalid duration subtitles

                try:
                    # Log video dimensions and text width calculation
                    self.logger.info(f"Video dimensions: {video_clip.w}x{video_clip.h}")
                    self.logger.info(
                        f"Text: '{text[:30]}...' (length: {len(text)} chars)"
                    )

                    # Split long text into multiple lines if necessary
                    # Use dynamic character limit based on content and screen width
                    max_text_width = int(
                        video_clip.w * 0.65
                    )  # Reduced to 65% for mobile safety
                    max_chars_per_line = calculate_safe_max_chars(text, max_text_width)
                    self.logger.info(
                        f"Dynamic character limit: {max_chars_per_line} chars for text: '{text[:30]}...'"
                    )
                    text_lines = split_long_subtitle_text(text, max_chars_per_line)

                    # If text was split into multiple lines, create separate text clips for each line
                    if len(text_lines) > 1:
                        self.logger.info(
                            f"Split long text into {len(text_lines)} lines: '{text[:30]}...'"
                        )

                        text_clips = []
                        line_height = font_size + 5  # Spacing between lines

                        for i, line_text in enumerate(text_lines):
                            # Calculate maximum text width for mobile portrait video with proper margins
                            # For 1080px width: 15% margins = 162px each side, text area = 756px
                            max_text_width = int(
                                video_clip.w * 0.65
                            )  # Reduced to 65% for mobile safety
                            self.logger.info(
                                f"Max text width: {max_text_width}px ({max_text_width / video_clip.w * 100:.1f}% of video width)"
                            )

                            line_clip = TextClip(
                                subtitle_font,
                                line_text,
                                font_size=font_size,
                                color="white",
                                stroke_color="black",
                                stroke_width=1,
                                size=(max_text_width, None),  # Strict width limit
                                method="caption",  # Enable text wrapping
                                text_align="center",  # Center alignment
                                transparent=True,
                            )

                            # Log actual rendered text width
                            self.logger.info(
                                f"Rendered line width: {line_clip.w}px (limit: {max_text_width}px) - text: '{line_text[:20]}...'"
                            )

                            # Position each line (stacked vertically and centered)
                            y_position = subtitle_position / 100 * video_clip.h
                            subtitle_x = (
                                video_clip.w / 2 - line_clip.w / 2
                            )  # Center horizontally
                            subtitle_y = (
                                y_position
                                - (len(text_lines) - 1) * line_height / 2
                                + i * line_height
                            )

                            # Safety check: if text is still too wide, enforce strict limits
                            if line_clip.w > max_text_width:
                                self.logger.warning(
                                    f"Text line still too wide: {line_clip.w} > {max_text_width}"
                                )
                                line_clip.close()

                                # Try with much smaller font size - more aggressive reduction for mobile
                                # For Chinese text, use even more aggressive reduction
                                if contains_chinese(line_text):
                                    emergency_font_size = max(
                                        16, int(font_size * 0.4)
                                    )  # 40% reduction for Chinese
                                else:
                                    emergency_font_size = max(
                                        16, int(font_size * 0.5)
                                    )  # 50% reduction for English
                                self.logger.info(
                                    f"Emergency font size reduction: {font_size} → {emergency_font_size}"
                                )

                                line_clip = TextClip(
                                    subtitle_font,
                                    line_text,
                                    font_size=emergency_font_size,
                                    color="white",
                                    stroke_color="black",
                                    stroke_width=1,
                                    size=(max_text_width, None),
                                    method="caption",
                                    text_align="center",
                                    transparent=True,
                                )
                                # Recalculate position with new size
                                subtitle_x = video_clip.w / 2 - line_clip.w / 2  # type: ignore

                                # Final safety check - if still too wide, force width scaling
                                if line_clip.w > max_text_width:  # type: ignore
                                    self.logger.error(
                                        f"Text line still exceeds width after emergency reduction: {line_clip.w} > {max_text_width}"  # type: ignore
                                    )
                                    # Force scale the text clip width to fit exactly
                                    force_scale = max_text_width / line_clip.w  # type: ignore
                                    line_clip = line_clip.with_effects(
                                        [vfx.Resize(new_size=force_scale)]
                                    )
                                    subtitle_x = video_clip.w / 2 - line_clip.w / 2  # type: ignore
                                    self.logger.info(
                                        f"Applied forced scaling: {force_scale:.2f}x"
                                    )
                                    self.logger.error(
                                        "WARNING: Text was scaled down to fit - consider shortening subtitle text"
                                    )

                            if line_clip:
                                line_clip = line_clip.with_position(  # type: ignore
                                    (subtitle_x, subtitle_y)
                                )
                                line_clip = line_clip.with_start(start_time)  # type: ignore
                                line_clip = line_clip.with_duration(subtitle_duration)  # type: ignore
                                text_clips.append(line_clip)

                        subtitle_clips.extend(text_clips)
                        continue  # Skip the single-line processing below
                    else:
                        # Single line text processing
                        # Calculate maximum text width for mobile portrait video with proper margins
                        # For 1080px width: 15% margins = 162px each side, text area = 756px
                        max_text_width = int(
                            video_clip.w * 0.65
                        )  # Reduced to 65% for mobile safety
                        self.logger.info(
                            f"Max text width: {max_text_width}px ({max_text_width / video_clip.w * 100:.1f}% of video width)"
                        )

                        text_clip = TextClip(
                            subtitle_font,
                            text,
                            font_size=font_size,
                            color="white",
                            stroke_color="black",
                            stroke_width=1,
                            size=(max_text_width, None),  # Strict width limit
                            method="caption",  # Enable text wrapping
                            text_align="center",  # Center alignment
                            transparent=True,
                        )

                        # Log actual rendered text width
                        self.logger.info(
                            f"Rendered text width: {text_clip.w}px (limit: {max_text_width}px) - text: '{text[:20]}...'"
                        )

                        # Position subtitle (centered)
                        y_position = subtitle_position / 100 * video_clip.h
                        subtitle_x = video_clip.w / 2 - text_clip.w / 2
                        subtitle_y = y_position

                        # Additional safety check: if text is still too wide, enforce strict limits
                        if text_clip.w > max_text_width:
                            self.logger.warning(
                                f"Text still too wide after wrapping: {text_clip.w} > {max_text_width}"
                            )
                            text_clip.close()

                            # Try with much smaller font size - more aggressive reduction for mobile
                            # For Chinese text, use even more aggressive reduction
                            if contains_chinese(text):
                                emergency_font_size = max(
                                    16, int(font_size * 0.4)
                                )  # 40% reduction for Chinese
                            else:
                                emergency_font_size = max(
                                    16, int(font_size * 0.5)
                                )  # 50% reduction for English
                            self.logger.info(
                                f"Emergency font size reduction: {font_size} → {emergency_font_size}"
                            )

                            text_clip = TextClip(
                                subtitle_font,
                                text,
                                font_size=emergency_font_size,
                                color="white",
                                stroke_color="black",
                                stroke_width=1,
                                size=(max_text_width, None),
                                method="caption",
                                text_align="center",
                                transparent=True,
                            )
                            # Recalculate position with new size
                            subtitle_x = video_clip.w / 2 - text_clip.w / 2

                            # Final safety check - if still too wide, force width scaling
                            if text_clip.w > max_text_width:
                                self.logger.error(
                                    f"Text still exceeds width after emergency reduction: {text_clip.w} > {max_text_width}"
                                )
                                # Force scale the text clip width to fit exactly
                                force_scale = max_text_width / text_clip.w
                                text_clip = text_clip.with_effects(
                                    [vfx.Resize(new_size=force_scale)]
                                )
                                subtitle_x = video_clip.w / 2 - text_clip.w / 2
                                self.logger.info(
                                    f"Applied forced scaling: {force_scale:.2f}x"
                                )
                                self.logger.error(
                                    "WARNING: Text was scaled down to fit - consider shortening subtitle text"
                                )

                            self.logger.info(
                                f"Emergency font size reduction completed: {emergency_font_size}"
                            )

                    # Set timing and position
                    if text_clip:
                        text_clip = text_clip.with_position((subtitle_x, subtitle_y))
                        text_clip = text_clip.with_start(start_time)
                        text_clip = text_clip.with_duration(subtitle_duration)
                        subtitle_clips.append(text_clip)
                    self.logger.debug(
                        f"Added subtitle: '{text[:30]}...' at {start_time:.2f}s for {subtitle_duration:.2f}s"
                    )

                except Exception as e:
                    self.logger.error(
                        f">>>Failed to create subtitle clip for '{text}': {e}"
                    )
                    continue

            if subtitle_clips:
                # Composite all subtitle clips with the main video
                result = CompositeVideoClip([video_clip] + subtitle_clips)
                self.logger.info(
                    f"Successfully added {len(subtitle_clips)} subtitles to video"
                )
                return result
            else:
                self.logger.warning("No subtitle clips were created successfully")
                return video_clip

        except Exception as e:
            self.logger.error(f"Failed to add timestamped subtitles: {e}")
            return video_clip

    def apply_transition(self, clip1, clip2):
        """Apply random transition between clips"""
        transitions = [
            lambda c1, _: c1.crossfadeout(0.5),
            lambda _, c2: c2.with_effects(FadeIn(0.5)),
            lambda c1, _: c1.with_effects(FadeOut(0.5)),
        ]

        transition = random.choice(transitions)
        return transition(clip1, clip2)

    def _check_and_regenerate_aspect_ratio(self, video_file):
        """Check if video is 16:9 aspect ratio and regenerate if not"""
        import subprocess
        import json

        try:
            # Get video dimensions using ffprobe

            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(video_file),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                self.logger.error(
                    f"ffprobe failed with exit code {result.returncode}: {result.stderr}"
                )
                return False
            if not result.stdout:
                self.logger.error("ffprobe returned no output")
                return False

            video_info = json.loads(result.stdout)

            # Find video stream
            video_stream = None
            for stream in video_info.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_stream = stream
                    break

            if not video_stream:
                self.logger.error("No video stream found in the file")
                return False

            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))

            if width == 0 or height == 0:
                self.logger.error("Invalid video dimensions")
                return False

            # For mobile phone portrait video: height > width, 16:9 ratio means height:width = 16:9
            # So target ratio should be height/width = 16/9 = 1.777...
            is_portrait = height > width

            if is_portrait:
                # Portrait mode: height/width should be 16/9
                portrait_ratio = height / width
                target_portrait_ratio = 16 / 9  # 1.777...

                # Standard mobile portrait sizes (height x width)
                standard_portrait_sizes = [
                    (1920, 1080),  # Full HD portrait
                    (1280, 720),  # HD portrait
                    (960, 540),  # qHD portrait
                    (854, 480),  # FWVGA portrait
                ]

                is_standard_ratio = (height, width) in standard_portrait_sizes
                tolerance = 0.001  # 0.1% tolerance
                is_correct_ratio = (
                    abs(portrait_ratio - target_portrait_ratio) < tolerance
                )
                final_check = is_standard_ratio or is_correct_ratio

                self.logger.info(
                    f"Portrait mode detected: {width}x{height}, Ratio: {portrait_ratio:.3f}, Target 16:9 portrait: {target_portrait_ratio:.3f}"
                )
                self.logger.info(
                    f"Standard mobile portrait: {is_standard_ratio}, Ratio match: {is_correct_ratio}"
                )

                if final_check:
                    print(
                        f"✅ Mobile portrait aspect ratio is correct: {width}x{height} ({portrait_ratio:.3f})"
                    )
                    return False
                else:
                    print(
                        f"❌ Mobile portrait aspect ratio is incorrect: {width}x{height} ({portrait_ratio:.3f})"
                    )
                    print(f"   Target 16:9 portrait ratio: {target_portrait_ratio:.3f}")
                    print(
                        "🔄 Regenerating video with correct mobile 16:9 portrait ratio..."
                    )
                    return self._regenerate_with_mobile_portrait_ratio(
                        video_file, width, height
                    )
            else:
                # Landscape mode (not what we want for mobile)
                print(
                    f"❌ Video is in landscape mode {width}x{height}, but mobile requires portrait mode"
                )
                print("🔄 Regenerating video with mobile portrait orientation...")
                return self._regenerate_with_mobile_portrait_ratio(
                    video_file, width, height
                )

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get video info: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error checking aspect ratio: {e}")
            return False

    def _regenerate_with_mobile_portrait_ratio(
        self, video_file, current_width, current_height
    ):
        """Regenerate video by cropping from center to 9:16 (width:height) aspect ratio"""

        try:
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
                x_offset = (current_width - new_width) // 2
                y_offset = 0
            else:
                # Video is too tall, crop height
                new_width = current_width
                new_height = int(current_width / target_ratio)
                x_offset = 0
                y_offset = (current_height - new_height) // 2

            self.logger.info(f"Original video: {current_width}x{current_height}")
            self.logger.info(f"Cropping to: {new_width}x{new_height} from center")
            self.logger.info(f"Crop offset: {x_offset}x{y_offset}")

            # Use ffmpeg to crop from center (maintaining original aspect ratio)
            # First crop to 9:16 ratio, then scale to standard mobile size
            target_width, target_height = 1080, 1920  # Standard mobile portrait size

            cmd = [
                "ffmpeg",
                "-i",
                str(video_file),
                "-vf",
                f"crop={new_width}:{new_height}:{x_offset}:{y_offset},scale={target_width}:{target_height}",
                "-c:v",
                "libx264",
                "-c:a",
                "copy",  # Keep original audio
                "-preset",
                "medium",
                "-crf",
                "23",
                "-y",  # Overwrite output file
                str(temp_file),
            ]

            print("🎬 Regenerating mobile portrait video with center cropping...")
            subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Replace original file with corrected one
            if temp_file.exists():
                # Backup original file
                backup_file = video_file.with_suffix(".backup.mp4")
                if video_file.exists():
                    video_file.rename(backup_file)

                # Move corrected file to original location
                temp_file.rename(video_file)

                self.logger.info(
                    f"Mobile portrait video regenerated successfully: {target_width}x{target_height}"
                )
                print(
                    f"✅ Mobile portrait video regenerated successfully: {target_width}x{target_height}"
                )
                print(f"   Cropped from center: {new_width}x{new_height}")
                print("   Maintained original video aspect ratio (no distortion)")
                print("   Standard mobile 9:16 aspect ratio (width:height)")
                print(f"   Original file backed up as: {backup_file.name}")
                return True
            else:
                self.logger.error("Temp file not created")
                return False

        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg failed: {e}")
            if e.stderr:
                self.logger.error(f"FFmpeg stderr: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Error regenerating mobile portrait video: {e}")
            return False

    def create_final_video(self):
        """Create the final video with proper workflow: generate content → create video → trim to audio → add audio → prepend start → append end"""
        self.logger.info("Starting video generation process...")
        print("🎬 Starting video generation process...")

        # Step 1: Generate subtitles and audio
        self.logger.info("Step 1: Generating subtitles and audio...")
        print("📝 Step 1: Generating subtitles and audio...")

        # New logic for subtitle and audio generation:
        # If --text provided: use specified text file as subtitles
        # If neither --gen-subtitle nor --gen-voice: use existing files
        # If only --gen-subtitle: generate subtitles + voice
        # If only --gen-voice: use existing subtitles + generate voice
        # If both --gen-subtitle and --gen-voice: generate both

        # Check if --text parameter is provided (highest priority)
        if self.args.text:
            self.logger.info(f"Using text file: {self.args.text}")
            if self.subtitle_processor.load_text_file_subtitles(self, self.args.text):
                # Text file loaded successfully, now decide about voice generation
                if self.args.gen_voice:
                    self.logger.info("Generating voice for text file subtitles...")
                    self.audioGenerator.generate_audio(self)
                    self.subtitle_processor._calculate_subtitle_timestamps(self)
                else:
                    # Check if existing audio file exists
                    audio_file = self.project_folder / "generated_audio.mp3"
                    if audio_file.exists():
                        self.audio_file = audio_file
                        self.logger.info("Using existing audio file")
                        # Calculate subtitle timestamps using existing audio
                        self.subtitle_processor._calculate_subtitle_timestamps(self)
                    else:
                        raise FileNotFoundError(
                            "No audio file found. Use --gen-voice to generate audio."
                        )
            else:
                raise FileNotFoundError(
                    f"Failed to load subtitles from text file: {self.args.text}"
                )
        else:
            # Standard logic without --text parameter
            subtitle_needs_generation = self.args.gen_subtitle
            voice_needs_generation = self.args.gen_voice

            self.logger.info(
                f"Subtitle generation: {'YES' if subtitle_needs_generation else 'NO'}"
            )
            self.logger.info(
                f"Voice generation: {'YES' if voice_needs_generation else 'NO'}"
            )

            # Load subtitles if not generating them
            if not subtitle_needs_generation:
                # Try to load existing generated subtitles first
                if self.subtitle_processor.load_existing_subtitles(self):
                    self.logger.info("Using existing generated subtitles")
                else:
                    # If no existing generated subtitles, try static files
                    if self.subtitle_processor.load_static_subtitles():
                        self.logger.info("Using static subtitle files")
                    else:
                        raise FileNotFoundError(
                            "No subtitles found. Use --gen-subtitle to generate subtitles."
                        )
            else:
                # Generate new subtitles
                self.logger.info("Generating new subtitles...")
                self.voice_subtitles, self.display_subtitles = (
                    self.llm_manager.generate_subtitles(
                        self.args, self.prompt_folder, self.subtitle_folder, self.logger
                    )
                )
                # Use display subtitles for the main workflow (backward compatibility)
                self.subtitles = self.display_subtitles
                self.subtitle_processor._log_subtitles("LLM - Generated")

            # Generate audio if needed
            if voice_needs_generation:
                self.logger.info("Generating new audio...")
                self.audioGenerator.generate_audio(self)
                self.subtitle_processor._calculate_subtitle_timestamps(self)
            else:
                # Check if existing audio file exists
                audio_file = self.project_folder / "generated_audio.mp3"
                if audio_file.exists():
                    self.audio_file = audio_file
                    self.logger.info("Using existing audio file")
                    # Calculate subtitle timestamps using existing audio (for both existing and new subtitles)
                    if hasattr(self, "voice_subtitles") and self.voice_subtitles:
                        self.subtitle_processor._calculate_subtitle_timestamps(self)
                else:
                    raise FileNotFoundError(
                        "No audio file found. Use --gen-voice to generate audio."
                    )

        # Step 2: Create main video content
        self.logger.info("Step 2: Creating main video content...")

        # Scan media files
        self.scan_media_files()

        # Get audio duration to match main content
        audio_duration = None
        if self.audio_file and self.audio_file.exists():
            try:
                audio_duration = AudioFileClip(str(self.audio_file)).duration
                self.logger.info(
                    f"Generated audio duration: {audio_duration:.2f} seconds"
                )
            except Exception as e:
                self.logger.warning(f"Could not get audio duration: {e}")

        # Set main content target duration to match audio
        if audio_duration:
            main_target_duration = audio_duration
            self.logger.info(
                f"Main content target duration (matching audio): {main_target_duration:.2f}s"
            )
        else:
            main_target_duration = getattr(self.args, "length", 30.0)
            if main_target_duration is None:
                main_target_duration = 30.0
            self.logger.info(
                f"Main content target duration (from args): {main_target_duration:.2f}s"
            )

        # Process main clips to match target duration
        original_length = getattr(self.args, "length", None)
        self.args.length = main_target_duration

        print("🎬 Step 2: Creating main video content...")
        main_clips = self.process_media_clips()

        # Restore original length
        self.args.length = original_length

        # Process main clips with titles only (subtitles added later to entire video)
        processed_main_clips = []
        for i, clip in enumerate(main_clips):
            # Add title to clips
            if self.args.title:
                # If keep_title is enabled, add title to all clips with full duration
                # Otherwise, only add title to first clip with limited duration
                if getattr(self.args, "keep_title", False):
                    clip = self.title_processor.add_title(
                        self.args, clip, self.args.title
                    )
                elif i == 0:
                    clip = self.title_processor.add_title(
                        self.args, clip, self.args.title
                    )

            # Note: Subtitles are now added to the entire video later using timestamp-based synchronization
            # The old per-clip subtitle assignment has been removed

            # Ensure clip has duration
            if hasattr(clip, "duration") and clip.duration is not None:
                processed_main_clips.append(clip)
            else:
                self.logger.warning(f"Skipping main clip {i} due to None duration")

        # Concatenate main clips to create main content
        if len(processed_main_clips) == 0:
            raise ValueError("No main clips available for video creation")

        if len(processed_main_clips) == 1:
            main_content = processed_main_clips[0]
            self.logger.info("Single main clip, no concatenation needed")
        else:
            self.logger.info("Concatenating main clips")
            main_content = self._safe_concatenate_clips(
                processed_main_clips, method="compose"
            )

        main_content_duration = main_content.duration
        self.logger.info(f"Main content duration: {main_content_duration:.2f}s")
        print(f"✅ Main content created: {main_content_duration:.2f}s")

        # Step 3: Trim main video to match audio length
        self.logger.info("Step 3: Trimming main video to match audio length...")
        print("✂️  Step 3: Trimming main video to match audio length...")

        if audio_duration and self.audio_file and self.audio_file.exists():
            try:
                # Get audio duration for comparison
                audio_clip_check = AudioFileClip(str(self.audio_file))
                actual_audio_duration = audio_clip_check.duration
                audio_clip_check.close()

                self.logger.info(f"Audio duration: {actual_audio_duration:.2f}s")
                self.logger.info(f"Main content duration: {main_content_duration:.2f}s")

                if main_content_duration > actual_audio_duration:
                    # Trim main content to match audio duration
                    self.logger.info(
                        f"Trimming main content from {main_content_duration:.2f}s to {actual_audio_duration:.2f}s"
                    )
                    main_content = main_content.subclipped(0, actual_audio_duration)
                    self.logger.info(
                        f"Main content trimmed to: {main_content.duration:.2f}s"
                    )
                elif main_content_duration < actual_audio_duration:
                    self.logger.info(
                        f"Main content ({main_content_duration:.2f}s) is shorter than audio ({actual_audio_duration:.2f}s) - keeping as is"
                    )
                else:
                    self.logger.info("Main content and audio durations match perfectly")

            except Exception as e:
                self.logger.warning(f"Failed to trim main content to audio length: {e}")
                self.logger.info("Continuing with original main content duration")

        # Step 4: Add audio to main content
        self.logger.info("Step 4: Adding audio to main content...")
        print("🎵 Step 4: Adding audio to main content...")

        if audio_duration and self.audio_file and self.audio_file.exists():
            try:
                audio = AudioFileClip(str(self.audio_file))
                if audio:
                    self.logger.info(f"Audio duration: {audio.duration:.2f}s")

                # Now durations should match perfectly, but double-check
                if audio and abs(main_content.duration - audio.duration) > 0.1:
                    self.logger.warning(
                        f"Duration mismatch after trimming: video={main_content.duration:.2f}s, audio={audio.duration:.2f}s"
                    )
                    # Trim audio to match video duration as final safeguard
                    if audio and audio.duration > main_content.duration:
                        audio = audio.subclipped(0, main_content.duration)
                        if audio:
                            self.logger.info(
                                f"Trimmed audio to match video: {audio.duration:.2f}s"
                            )

                # Apply audio to main content
                main_content = main_content.with_audio(audio)
                self.logger.info(
                    f"Main content with audio duration: {main_content.duration:.2f}s"
                )

                # Step 4.5: Add timestamped subtitles to main content
                self.logger.info(
                    "Step 4.5: Adding timestamped subtitles to main content..."
                )
                print("📝 Step 4.5: Adding timestamped subtitles to main content...")
                main_content = self.add_timestamped_subtitles(main_content)
                self.logger.info(
                    f"Main content with subtitles duration: {main_content.duration:.2f}s"
                )
                print(f"✅ Timestamped subtitles added: {main_content.duration:.2f}s")

            except Exception as e:
                self.logger.error(f"Failed to add audio: {e}")
                print(f"Damn, failed to add audio: {e}")

        # Step 5: Prepend starting clip
        self.logger.info("Step 5: Prepending starting clip...")
        print("🎬 Step 5: Adding starting clip...")

        final_clips = []

        # Add start clip if available
        if self.start_file:
            start_clip = self._safe_load_video_clip(self.start_file)
            if start_clip is not None:
                # Resize start clip to fit mobile aspect ratio (remove black borders)
                start_clip = self._resize_to_mobile_aspect_ratio(start_clip)
                self.logger.info(
                    f"Resized start clip to mobile aspect ratio: {start_clip.w}x{start_clip.h}"
                )

                # Make start clip silent if requested
                start_clip = start_clip.without_audio()
                # Add title to start clip if we have a title
                if self.args.title:
                    start_clip = self.title_processor.add_title(
                        self.args, start_clip, self.args.title
                    )
                final_clips.append(start_clip)
                self.logger.info(f"Added start clip: {start_clip.duration:.2f}s")
            else:
                self.logger.warning(f"Skipping corrupted start clip: {self.start_file}")

        # Add main content with audio
        final_clips.append(main_content)

        # Step 6: Append ending clip
        self.logger.info("Step 6: Appending ending clip...")
        print("🎬 Step 6: Adding ending clip...")

        # Add closing clip if available
        if self.closing_file:
            closing_clip = self._safe_load_video_clip(self.closing_file)
            if closing_clip is not None:
                # Resize closing clip to fit mobile aspect ratio (remove black borders)
                closing_clip = self._resize_to_mobile_aspect_ratio(closing_clip)
                self.logger.info(
                    f"Resized closing clip to mobile aspect ratio: {closing_clip.w}x{closing_clip.h}"
                )

                # Make closing clip silent if requested
                closing_clip = closing_clip.without_audio()
                final_clips.append(closing_clip)
                self.logger.info(f"Added closing clip: {closing_clip.duration:.2f}s")
            else:
                self.logger.warning(
                    f"Skipping corrupted closing clip: {self.closing_file}"
                )

        # Step 7: Create final video
        self.logger.info("Step 7: Creating final video...")
        print("🎬 Step 7: Creating final video...")

        # Calculate total duration
        total_duration = sum(
            c.duration
            for c in final_clips
            if hasattr(c, "duration") and c.duration is not None
        )
        self.logger.info(f"Final video duration: {total_duration:.2f}s")

        # Concatenate all clips
        if len(final_clips) == 1:
            final_clip = final_clips[0]
            self.logger.info("Single clip, no concatenation needed")
        else:
            try:
                final_clip = self._safe_concatenate_clips(final_clips, method="compose")
                self.logger.info(
                    f"Successfully concatenated final video with {len(final_clips)} components"
                )
            except Exception as concat_error:
                self.logger.error(f"Failed to concatenate final clips: {concat_error}")
                # Fallback: use the main content
                final_clip = main_content
                self.logger.warning("Using main content as fallback")

        self.logger.info(f"Final video duration: {final_clip.duration:.2f}s")

        # Step 7.5: Add background music if specified
        if getattr(self.args, "mp3", None):
            self.logger.info("Step 7.5: Adding background music...")
            print("🎵 Step 7.5: Adding background music...")
            self.background_music_processor._add_background_music(final_clip)
            self.logger.info(
                f"Final video duration after adding background music: {final_clip.duration:.2f}s"
            )

        # Write output file
        output_file = self.project_folder / "output" / "output.mp4"
        self.logger.info(f"Writing video to: {output_file}")

        # Progress tracking for video writing using file size monitoring
        import threading

        def monitor_video_progress(file_path, expected_duration):
            """Monitor video file size to estimate progress"""
            start_time = time.time()
            last_size = 0
            last_check_time = start_time

            # Wait for file to be created
            while not file_path.exists():
                time.sleep(0.5)
                if time.time() - start_time > 30:  # 30 second timeout
                    return

            self.logger.info("Video writing in progress...")

            while True:
                try:
                    current_time = time.time()
                    current_size = (
                        file_path.stat().st_size if file_path.exists() else last_size
                    )

                    # Check if file is still being written (size changing)
                    if current_size > last_size or (current_time - last_check_time < 2):
                        elapsed = current_time - start_time

                        # Estimate progress based on elapsed time and expected duration
                        # Assume video encoding takes roughly 1.5x the video duration
                        estimated_total_time = expected_duration * 1.5
                        progress = min(
                            elapsed / estimated_total_time, 0.95
                        )  # Cap at 95%

                        percentage = progress * 100
                        remaining = (
                            estimated_total_time - elapsed if progress < 0.95 else 0
                        )

                        print(
                            f"Progress: {percentage:5.1f}% | Elapsed: {elapsed:4.0f}s | ETA: {remaining:4.0f}s | Size: {current_size / 1024 / 1024:6.1f}MB"
                        )

                        last_size = current_size
                        last_check_time = current_time

                        if progress >= 0.95:
                            print("Finalizing video...")
                            break
                    else:
                        # File size not changing, assume writing is complete
                        break

                    time.sleep(2)  # Check every 2 seconds

                except (OSError, FileNotFoundError):
                    # File might be temporarily inaccessible
                    time.sleep(0.5)
                    continue

        # Start progress monitoring in a separate thread
        progress_thread = threading.Thread(
            target=monitor_video_progress,
            args=(output_file, final_clip.duration),
            daemon=True,
        )
        progress_thread.start()

        # Optimize video writing parameters
        self.logger.info("Starting video rendering process... This may take a while")

        # Enable MoviePy's built-in progress bar but also add our own monitoring

        # Verify final_clip before writing
        if final_clip is None:
            raise ValueError("final_clip is None before write_videofile")

        # Test if the final clip can be read
        try:
            test_frame = final_clip.get_frame(0.0)
            if test_frame is None or not isinstance(test_frame, np.ndarray):
                raise ValueError("Cannot get frame from final_clip")
        except Exception as frame_error:
            raise ValueError(f"Cannot read frames from final_clip: {frame_error}")

        self.logger.info(
            f"Final clip validation passed: {final_clip.duration}s, {final_clip.w}x{final_clip.h}"
        )

        final_clip.write_videofile(
            str(output_file),
            codec="libx264",
            audio_codec="aac",
            fps=24,
            preset="fast",  # Use faster preset for quicker encoding
            threads=4,
            logger=None,  # Explicitly set logger to None to avoid stdout issues
            ffmpeg_params=[
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
            ],  # Ensure proper moov atom placement
        )

        # Wait for progress monitoring to finish
        progress_thread.join(timeout=5)

        self.logger.info("Video writing completed!")

        # Apply background music using FFmpeg if specified (post-processing approach)
        self.background_music_processor._apply_background_music_ffmpeg(output_file)

        self.logger.info(f"Video created successfully: {output_file}")
        self.logger.info(f"Video generation completed successfully: {output_file}")
        self.logger.info(f"Final video duration: {final_clip.duration:.2f} seconds")
        self.logger.info(f"Main content duration: {main_content_duration:.2f} seconds")
        if audio_duration:
            self.logger.info(f"Audio duration: {audio_duration:.2f} seconds")
        self.logger.info(f"Total components: {len(final_clips)}")
        self.logger.info(f"Total subtitles: {len(self.subtitles)}")

        # Clean up
        final_clip.close()
        for clip in final_clips:
            clip.close()
        if "main_content" in locals():
            main_content.close()

        # Check video aspect ratio and regenerate if not 16:9
        if self._check_and_regenerate_aspect_ratio(output_file):
            self.logger.info("Video regenerated with correct 16:9 aspect ratio")
            print("✅ Video regenerated with correct 16:9 aspect ratio")

        self.logger.info("Video generation process finished.")

        # Show video length after generation
        self._show_video_length(output_file)
        if self.args.open:
            os.system(f"open {output_file}")

    def _show_video_length(self, video_path):
        """Show the duration of the generated video file."""
        try:
            from moviepy import VideoFileClip

            # Load the video file
            clip = VideoFileClip(str(video_path))

            # Get the duration in seconds
            duration = clip.duration

            # Close the clip to free resources
            clip.close()

            # Convert to minutes and seconds for better readability
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            milliseconds = int((duration % 1) * 1000)

            print(f"🎬 Generated video duration: {duration:.3f} seconds")
            print(
                f"   Duration: {minutes} minutes, {seconds} seconds, {milliseconds} milliseconds"
            )

        except Exception as e:
            self.logger.error(f"Failed to get video duration: {e}")
