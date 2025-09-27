#!/usr/bin/env python3
"""
Media Processing Module - Handles media file operations
Damn, don't mess with the media processing unless you know what you're doing!
"""

import random
import numpy as np

from moviepy import VideoFileClip, concatenate_videoclips


class MediaProcessor:
    """
    Media processing class - handles all media file operations
    Don't even think about touching the media logic!
    """

    def __init__(self, config_manager, logger):
        self.config = config_manager
        self.logger = logger
        self.args = config_manager.args

        # Get project paths
        paths = config_manager.get_project_paths()
        self.media_folder = paths["media"]

        # Media files list
        self.media_files = []
        self.start_file = None
        self.closing_file = None

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
                if file_path.stem.lower() in ["start", "starting"]:
                    self.start_file = file_path
                elif file_path.stem.lower() == "closing":
                    self.closing_file = file_path
                else:
                    all_files.append(file_path)

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

    def _safe_load_video_clip(self, file_path, max_duration_check=10.0):
        """Safely load a video clip with error handling for corrupted files"""
        try:
            # First try to get basic file info
            if not file_path.exists():
                self.logger.warning(f"File does not exist: {file_path}")
                return None

            # Try to load with a quick duration check first
            test_clip = VideoFileClip(str(file_path))

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
            if test_clip.duration > max_duration_check:
                # Try to read a frame from the beginning
                try:
                    subclip = test_clip.subclipped(0, min(1.0, test_clip.duration))
                    if subclip:
                        subclip.close()
                except Exception as frame_error:
                    self.logger.warning(
                        f"Failed to read initial frames from {file_path}: {frame_error}"
                    )
                    test_clip.close()
                    return None

                # Try to read a frame from near the end to detect corruption
                try:
                    end_check_start = max(0, test_clip.duration - max_duration_check)
                    subclip = test_clip.subclipped(end_check_start, test_clip.duration)
                    if subclip:
                        subclip.close()
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
                if test_frame is None or not isinstance(test_frame, np.ndarray):
                    self.logger.warning(
                        f"Skipping clip {i}: cannot read frames at start"
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
                    f"<<<Scaling up by factor {scale_factor:.2f} to {scaled_width}x{scaled_height}"
                )

                # Resize the clip
                scaled_clip = clip.resize((scaled_width, scaled_height))

                # Crop from center to target dimensions
                x_center = scaled_width // 2
                y_center = scaled_height // 2
                x1 = max(0, x_center - target_width // 2)
                x2 = min(scaled_width, x_center + target_width // 2)
                y1 = max(0, y_center - target_height // 2)
                y2 = min(scaled_height, y_center + target_height // 2)

                final_clip = scaled_clip.crop(x1=x1, y1=y1, x2=x2, y2=y2)

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
                cropped_clip = clip.crop(x1=x1, y1=y1, x2=x2, y2=y2)

                # Resize to target mobile resolution
                final_clip = cropped_clip.resize((target_width, target_height))

                self.logger.info(
                    f"Cropped and resized to mobile portrait: {target_width}x{target_height}"
                )

                # Clean up
                cropped_clip.close()

                return final_clip

        except Exception as e:
            self.logger.error(f"Error in _resize_to_mobile_aspect_ratio: {e}")
            return clip

