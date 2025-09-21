#!/usr/bin/env python3
"""
Video Repair Tool - Preprocess and repair videos with corrupted frames
This script detects and repairs videos with corrupted frames that cause issues in MoviePy
"""

import os
import sys
import cv2
import numpy as np
from pathlib import Path
import logging
from moviepy.editor import VideoFileClip
import argparse

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def detect_corrupted_frames(video_path, logger):
    """
    Detect corrupted frames in a video file
    Returns a list of corrupted frame indices
    """
    logger.info(f"Checking {video_path} for corrupted frames...")

    try:
        # Open video file
        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            logger.error(f"Cannot open video file: {video_path}")
            return []

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logger.info(f"Video info: {frame_count} frames, {fps} FPS, {width}x{height}")

        corrupted_frames = []
        valid_frames = []

        # Check each frame
        for i in range(frame_count):
            ret, frame = cap.read()

            if not ret:
                logger.warning(f"Frame {i} could not be read")
                corrupted_frames.append(i)
                continue

            # Check if frame is completely black or has invalid data
            if frame is None or frame.size == 0:
                logger.warning(f"Frame {i} is None or empty")
                corrupted_frames.append(i)
                continue

            # Check for frames with invalid pixel values
            if frame.min() < 0 or frame.max() > 255:
                logger.warning(f"Frame {i} has invalid pixel values")
                corrupted_frames.append(i)
                continue

            # Store valid frames for statistical analysis
            valid_frames.append(i)

        cap.release()

        # Additional check: if most frames are corrupted, the whole video might be problematic
        if frame_count > 0 and len(corrupted_frames) > frame_count * 0.5:
            logger.warning(f"More than 50% of frames are corrupted in {video_path}")
        elif len(corrupted_frames) > 0:
            logger.info(f"Found {len(corrupted_frames)} corrupted frames: {corrupted_frames}")
        else:
            logger.info("No corrupted frames detected")

        return corrupted_frames

    except Exception as e:
        logger.error(f"Error checking video {video_path}: {e}")
        return []

def repair_video(input_path, output_path, logger):
    """
    Repair a video by re-encoding it, which removes corrupted frames
    """
    logger.info(f"Repairing video: {input_path} -> {output_path}")

    try:
        # Use MoviePy to re-encode the video
        clip = VideoFileClip(str(input_path))

        # Check if clip is valid
        if not hasattr(clip, 'duration') or clip.duration is None or clip.duration <= 0:
            logger.error(f"Invalid video clip: {input_path}")
            clip.close()
            return False

        # Write the video with repair settings
        # Use a temporary file to avoid conflicts
        temp_output = str(output_path) + ".tmp.mp4"
        clip.write_videofile(
            temp_output,
            codec='libx264',
            audio_codec='aac',
            preset='ultrafast',  # Fast encoding for repair
            threads=4,
            fps=24,  # Standard frame rate
            verbose=False,
            logger=None
        )

        clip.close()

        # Move temp file to final output
        os.rename(temp_output, str(output_path))
        logger.info(f"Video repaired successfully: {output_path}")

        # Verify the repaired video
        try:
            test_clip = VideoFileClip(str(output_path))
            if hasattr(test_clip, 'duration') and test_clip.duration is not None and test_clip.duration > 0:
                test_clip.close()
                logger.info("Repaired video verified successfully")
                return True
            else:
                test_clip.close()
                logger.error("Repaired video is still invalid")
                return False
        except Exception as verify_error:
            logger.error(f"Failed to verify repaired video: {verify_error}")
            return False

    except Exception as e:
        logger.error(f"Failed to repair video {input_path}: {e}")
        return False

def process_media_folder(media_folder, logger):
    """
    Process all video files in a media folder
    """
    media_folder = Path(media_folder)

    if not media_folder.exists():
        logger.error(f"Media folder does not exist: {media_folder}")
        return

    # Video file extensions
    video_extensions = {'.mov', '.mp4', '.avi', '.mkv', '.wmv', '.flv'}

    # Find all video files
    video_files = []
    for file_path in media_folder.iterdir():
        if file_path.suffix.lower() in video_extensions:
            video_files.append(file_path)

    logger.info(f"Found {len(video_files)} video files")

    # Process each video file
    for video_file in video_files:
        logger.info(f"Processing {video_file.name}...")

        # Check for corrupted frames
        corrupted_frames = detect_corrupted_frames(video_file, logger)

        if corrupted_frames or len(corrupted_frames) > 0:
            # Create repaired version
            repaired_path = video_file.parent / f"repaired_{video_file.name}"
            success = repair_video(video_file, repaired_path, logger)

            if success:
                logger.info(f"Created repaired version: {repaired_path}")
                # Optional: Provide instructions for replacing the original
                logger.info(f"To use the repaired version, rename {repaired_path.name} to {video_file.name}")
            else:
                logger.error(f"Failed to repair {video_file}")
        else:
            logger.info(f"No issues found in {video_file.name}")


def repair_with_ffmpeg(input_path, output_path, logger):
    """
    Alternative repair method using ffmpeg directly for better control
    """
    try:
        import subprocess

        logger.info(f"Repairing with ffmpeg: {input_path} -> {output_path}")

        # ffmpeg command to repair video - handle corrupted frames and ensure video stream is processed
        cmd = [
            'ffmpeg',
            '-i', str(input_path),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-preset', 'ultrafast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-avoid_negative_ts', 'make_zero',
            '-fflags', '+genpts',
            '-vsync', '0',
            '-video_track_timescale', '90000',
            '-max_interleave_delta', '0',
            '-f', 'mp4',
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout

        if result.returncode == 0:
            logger.info(f"FFmpeg repair successful: {output_path}")
            return True
        else:
            logger.error(f"FFmpeg repair failed: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"FFmpeg repair error: {e}")
        return False


def auto_repair_videos(media_folder, logger, method='moviepy'):
    """
    Automatically repair all videos in a folder with corrupted frames
    """
    media_folder = Path(media_folder)

    if not media_folder.exists():
        logger.error(f"Media folder does not exist: {media_folder}")
        return

    # Video file extensions
    video_extensions = {'.mov', '.mp4', '.avi', '.mkv', '.wmv', '.flv'}

    # Find all video files
    video_files = []
    for file_path in media_folder.iterdir():
        if file_path.suffix.lower() in video_extensions:
            video_files.append(file_path)

    logger.info(f"Auto-repairing {len(video_files)} video files using {method} method")

    repaired_count = 0
    failed_count = 0

    # Process each video file
    for video_file in video_files:
        logger.info(f"Checking {video_file.name}...")

        # Check for corrupted frames
        corrupted_frames = detect_corrupted_frames(video_file, logger)

        if corrupted_frames or len(corrupted_frames) > 0:
            # Create repaired version
            repaired_path = video_file.parent / f"repaired_{video_file.name}"

            if method == 'ffmpeg':
                success = repair_with_ffmpeg(video_file, repaired_path, logger)
            else:
                success = repair_video(video_file, repaired_path, logger)

            if success:
                logger.info(f"✓ Repaired: {video_file.name}")
                repaired_count += 1
            else:
                logger.error(f"✗ Failed to repair: {video_file.name}")
                failed_count += 1
        else:
            logger.info(f"✓ No issues: {video_file.name}")

    logger.info(f"Auto-repair complete: {repaired_count} repaired, {failed_count} failed")

def main():
    """Main function"""
    logger = setup_logging()
    logger.info("Video Repair Tool Started")

    parser = argparse.ArgumentParser(description="Repair videos with corrupted frames")
    parser.add_argument("--folder", help="Media folder containing video files")
    parser.add_argument("--file", help="Specific video file to repair")
    parser.add_argument("--auto-repair", action="store_true", help="Automatically repair all videos with issues")
    parser.add_argument("--method", choices=['moviepy', 'ffmpeg'], default='moviepy',
                       help="Repair method to use (default: moviepy)")

    args = parser.parse_args()

    # Must specify either --folder or --file
    if not args.folder and not args.file:
        logger.error("Must specify either --folder or --file")
        return

    if args.file:
        # Process specific file
        file_path = Path(args.file)
        if not file_path.exists():
            logger.error(f"File does not exist: {file_path}")
            return

        logger.info(f"Processing specific file: {file_path}")
        corrupted_frames = detect_corrupted_frames(file_path, logger)

        if corrupted_frames:
            repaired_path = file_path.parent / f"repaired_{file_path.name}"
            if args.method == 'ffmpeg':
                success = repair_with_ffmpeg(file_path, repaired_path, logger)
            else:
                success = repair_video(file_path, repaired_path, logger)

            if success:
                logger.info(f"Repaired file saved as: {repaired_path}")
            else:
                logger.error("Failed to repair file")
        else:
            logger.info("No corrupted frames detected")
    elif args.auto_repair:
        # Auto-repair entire folder
        auto_repair_videos(args.folder, logger, args.method)
    else:
        # Process entire folder
        process_media_folder(args.folder, logger)

    logger.info("Video Repair Tool Finished")

if __name__ == "__main__":
    main()