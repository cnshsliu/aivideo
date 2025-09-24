#!/usr/bin/env python3
"""
Media Processor for AI Video Generator
Damn, this thing handles all the media file operations! Don't mess with it!
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
import random

from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip,
    concatenate_videoclips, vfx, ColorClip
)
from moviepy.video.fx import resize
import numpy as np

class MediaFile:
    """Media file representation"""

    def __init__(self, file_path: Path, file_type: str = "unknown"):
        self.file_path = file_path
        self.file_type = file_type
        self.duration = None
        self.resolution = None
        self.is_start = False
        self.is_closing = False
        self.metadata = {}

    def __str__(self):
        return f"MediaFile({self.file_path.name}, type={self.file_type})"

class MediaProcessor:
    """
    Media processing class - handles all the damn media files
    """

    def __init__(self, project_folder: Path, config_manager):
        self.project_folder = project_folder
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)

        # Media folders
        self.media_folder = project_folder / "media"
        self.output_folder = project_folder / "output"
        self.output_folder.mkdir(exist_ok=True)

        # Media files
        self.media_files: List[MediaFile] = []
        self.start_file: Optional[MediaFile] = None
        self.closing_file: Optional[MediaFile] = None

        # Supported formats
        self.video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        self.audio_extensions = {'.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a'}

    def scan_media_files(self) -> bool:
        """Scan media folder for media files"""
        if not self.media_folder.exists():
            self.logger.error(f"Media folder not found: {self.media_folder}")
            return False

        self.media_files.clear()

        # Scan for all media files
        for file_path in self.media_folder.iterdir():
            if file_path.is_file():
                file_ext = file_path.suffix.lower()
                media_file = MediaFile(file_path)

                if file_ext in self.video_extensions:
                    media_file.file_type = "video"
                    self._extract_video_metadata(media_file)
                elif file_ext in self.image_extensions:
                    media_file.file_type = "image"
                    self._extract_image_metadata(media_file)
                elif file_ext in self.audio_extensions:
                    media_file.file_type = "audio"
                    self._extract_audio_metadata(media_file)
                else:
                    continue  # Skip unsupported files

                # Check for special files
                self._check_special_files(media_file)
                self.media_files.append(media_file)

        # Sort files alphabetically
        self.media_files.sort(key=lambda x: x.file_path.name)

        self.logger.info(f"Found {len(self.media_files)} media files")
        self._log_media_summary()

        return len(self.media_files) > 0

    def _extract_video_metadata(self, media_file: MediaFile) -> None:
        """Extract metadata from video file"""
        try:
            with VideoFileClip(str(media_file.file_path)) as clip:
                media_file.duration = clip.duration
                media_file.resolution = (clip.w, clip.h)
                media_file.metadata = {
                    'fps': clip.fps,
                    'has_audio': clip.audio is not None
                }
        except Exception as e:
            self.logger.warning(f"Failed to extract metadata from {media_file.file_path}: {e}")

    def _extract_image_metadata(self, media_file: MediaFile) -> None:
        """Extract metadata from image file"""
        try:
            with ImageClip(str(media_file.file_path)) as clip:
                media_file.resolution = (clip.w, clip.h)
                # Images have default duration of 5 seconds
                media_file.duration = 5.0
                media_file.metadata = {
                    'is_image': True
                }
        except Exception as e:
            self.logger.warning(f"Failed to extract metadata from {media_file.file_path}: {e}")

    def _extract_audio_metadata(self, media_file: MediaFile) -> None:
        """Extract metadata from audio file"""
        try:
            with AudioFileClip(str(media_file.file_path)) as clip:
                media_file.duration = clip.duration
                media_file.metadata = {
                    'sample_rate': clip.fps,
                    'channels': 2 if clip.nchannels == 2 else 1
                }
        except Exception as e:
            self.logger.warning(f"Failed to extract metadata from {media_file.file_path}: {e}")

    def _check_special_files(self, media_file: MediaFile) -> None:
        """Check for special naming patterns"""
        filename = media_file.file_path.name.lower()

        if any(keyword in filename for keyword in ['start', 'begin', 'opening', 'intro']):
            media_file.is_start = True
            self.start_file = media_file
            self.logger.info(f"Found start file: {media_file.file_path.name}")

        if any(keyword in filename for keyword in ['end', 'close', 'closing', 'outro', 'finish']):
            media_file.is_closing = True
            self.closing_file = media_file
            self.logger.info(f"Found closing file: {media_file.file_path.name}")

    def _log_media_summary(self) -> None:
        """Log summary of media files"""
        by_type = {}
        for media_file in self.media_files:
            file_type = media_file.file_type
            if file_type not in by_type:
                by_type[file_type] = []
            by_type[file_type].append(media_file)

        for file_type, files in by_type.items():
            self.logger.info(f"{file_type.capitalize()} files: {len(files)}")
            for media_file in files[:5]:  # Show first 5
                prefix = ""
                if media_file.is_start:
                    prefix = "[START] "
                elif media_file.is_closing:
                    prefix = "[CLOSING] "
                self.logger.info(f"  {prefix}{media_file.file_path.name}")
                if media_file.duration:
                    self.logger.info(f"    Duration: {media_file.duration:.2f}s")
                if media_file.resolution:
                    self.logger.info(f"    Resolution: {media_file.resolution}")

    def get_regular_media_files(self) -> List[MediaFile]:
        """Get regular media files (excluding start and closing)"""
        return [f for f in self.media_files if not f.is_start and not f.is_closing]

    def get_video_files(self) -> List[MediaFile]:
        """Get only video files"""
        return [f for f in self.media_files if f.file_type == "video"]

    def get_image_files(self) -> List[MediaFile]:
        """Get only image files"""
        return [f for f in self.media_files if f.file_type == "image"]

    def safe_load_video_clip(self, file_path: Path, max_duration_check: float = 10.0) -> Optional[VideoFileClip]:
        """Safely load video clip with error handling"""
        try:
            # Quick duration check
            with VideoFileClip(str(file_path)) as clip:
                if clip.duration > max_duration_check:
                    self.logger.warning(f"Video too long ({clip.duration:.2f}s), truncating to {max_duration_check}s")
                    clip = clip.subclip(0, max_duration_check)
                return clip

        except Exception as e:
            self.logger.error(f"Failed to load video clip {file_path}: {e}")
            return None

    def resize_to_mobile_aspect_ratio(self, clip, target_width: int = None, target_height: int = None) -> VideoFileClip:
        """Resize clip to mobile aspect ratio"""
        if target_width is None:
            target_width = self.config_manager.get('video_settings.output_width', 1080)
        if target_height is None:
            target_height = self.config_manager.get('video_settings.output_height', 1920)

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

    def safe_concatenate_clips(self, clips: List, method: str = "compose") -> Optional[VideoFileClip]:
        """Safely concatenate video clips with error handling"""
        if not clips:
            return None

        try:
            if method == "compose":
                return concatenate_videoclips(clips, method="compose")
            else:
                return concatenate_videoclips(clips, method="chain")
        except Exception as e:
            self.logger.error(f"Failed to concatenate clips: {e}")
            return None

    def create_fade_transition(self, clip1: VideoFileClip, clip2: VideoFileClip, duration: float = 0.5) -> VideoFileClip:
        """Create fade transition between two clips"""
        try:
            # Add fade out to first clip
            clip1_fade = clip1.fadeout(duration)

            # Add fade in to second clip
            clip2_fade = clip2.fadein(duration)

            # Crossfade by overlaying
            return CompositeVideoClip([
                clip1_fade,
                clip2_fade.set_start(clip1.duration - duration)
            ])

        except Exception as e:
            self.logger.error(f"Failed to create fade transition: {e}")
            # Fallback to simple concatenation
            return concatenate_videoclips([clip1, clip2])

    def process_media_clips(self, target_duration: float = None, use_original_length: bool = False) -> Optional[VideoFileClip]:
        """Process media clips and create concatenated video"""
        if not self.media_files:
            self.logger.error("No media files found")
            return None

        video_files = self.get_video_files()
        if not video_files:
            self.logger.error("No video files found")
            return None

        if target_duration is None:
            target_duration = self.config_manager.get('video_settings.target_duration', 60)

        try:
            # Load all video clips
            clips = []
            for media_file in video_files:
                clip = self.safe_load_video_clip(media_file.file_path)
                if clip:
                    # Resize to mobile aspect ratio
                    clip = self.resize_to_mobile_aspect_ratio(clip)
                    clips.append(clip)

            if not clips:
                self.logger.error("No valid video clips loaded")
                return None

            # Process based on mode
            if use_original_length:
                return self._process_with_original_length(clips)
            else:
                return self._process_with_target_length(clips, target_duration)

        except Exception as e:
            self.logger.error(f"Error processing media clips: {e}")
            return None

    def _process_with_original_length(self, clips: List[VideoFileClip]) -> VideoFileClip:
        """Process clips using their original length"""
        self.logger.info("Processing clips with original length")

        # Add transitions between clips
        final_clips = []
        for i, clip in enumerate(clips):
            if i > 0:
                # Add transition
                transition = self.create_fade_transition(final_clips[-1], clip)
                # Remove the last clip and add the transition
                final_clips.pop()
                final_clips.append(transition)
            else:
                final_clips.append(clip)

        return self.safe_concatenate_clips(final_clips)

    def _process_with_target_length(self, clips: List[VideoFileClip], target_duration: float) -> VideoFileClip:
        """Process clips to match target duration"""
        self.logger.info(f"Processing clips to target duration: {target_duration}s")

        total_duration = sum(clip.duration for clip in clips)
        if total_duration <= target_duration:
            # If total duration is less than target, use all clips
            return self._process_with_original_length(clips)

        # Calculate how much to trim
        trim_ratio = target_duration / total_duration
        processed_clips = []

        for clip in clips:
            new_duration = clip.duration * trim_ratio
            # Cut from middle to avoid losing beginning/end
            start_time = (clip.duration - new_duration) / 2
            end_time = start_time + new_duration
            processed_clip = clip.subclip(start_time, end_time)
            processed_clips.append(processed_clip)

        return self._process_with_original_length(processed_clips)

    def validate_media_files(self) -> Dict[str, List[str]]:
        """Validate all media files and return issues"""
        issues = {
            'corrupted': [],
            'unsupported_format': [],
            'too_large': [],
            'too_short': [],
            'too_long': []
        }

        for media_file in self.media_files:
            try:
                if media_file.file_type == "video":
                    if media_file.duration:
                        if media_file.duration < 1.0:
                            issues['too_short'].append(str(media_file.file_path))
                        elif media_file.duration > 300:  # 5 minutes
                            issues['too_long'].append(str(media_file.file_path))

                elif media_file.file_type == "image":
                    if media_file.resolution:
                        width, height = media_file.resolution
                        if width > 4000 or height > 4000:
                            issues['too_large'].append(str(media_file.file_path))

            except Exception as e:
                issues['corrupted'].append(str(media_file.file_path))

        return issues

    def get_media_statistics(self) -> Dict[str, any]:
        """Get statistics about media files"""
        stats = {
            'total_files': len(self.media_files),
            'by_type': {},
            'total_duration': 0,
            'has_start_file': bool(self.start_file),
            'has_closing_file': bool(self.closing_file)
        }

        for media_file in self.media_files:
            file_type = media_file.file_type
            if file_type not in stats['by_type']:
                stats['by_type'][file_type] = {'count': 0, 'total_duration': 0}

            stats['by_type'][file_type]['count'] += 1
            if media_file.duration:
                stats['by_type'][file_type]['total_duration'] += media_file.duration
                stats['total_duration'] += media_file.duration

        return stats