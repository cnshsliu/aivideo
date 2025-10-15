#!/usr/bin/env python3
"""
Standalone script to read text from bodytext.txt and place it on sexygirl.mp4 video
"""

import os
import sys
from pathlib import Path
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, ColorClip
from moviepy.video.fx import FadeIn, FadeOut
import numpy as np

def contains_chinese(text):
    """Check if text contains Chinese characters"""
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            return True
    return False

def get_chinese_compatible_font(font_name="Arial"):
    """Get a Chinese-compatible font"""
    try:
        # Try common Chinese fonts
        chinese_fonts = ["SimHei", "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", "WenQuanYi Micro Hei"]
        for font in chinese_fonts:
            try:
                TextClip("测试", font_size=10, font=font).close()
                return font
            except:
                continue
        return "Arial"  # Fallback
    except:
        return "Arial"

def split_long_subtitle_text(text, max_chars_per_line):
    """Split long text into multiple lines"""
    if len(text) <= max_chars_per_line:
        return [text]

    lines = []
    current_line = ""

    for char in text:
        if len(current_line + char) <= max_chars_per_line:
            current_line += char
        else:
            if current_line:
                lines.append(current_line)
            current_line = char

    if current_line:
        lines.append(current_line)

    return lines

def calculate_safe_max_chars(text, max_text_width):
    """Calculate safe maximum characters per line"""
    # Estimate character width (rough approximation)
    avg_char_width = 20  # pixels per character
    max_chars = int(max_text_width / avg_char_width)

    # Adjust for Chinese characters (wider)
    if contains_chinese(text):
        max_chars = int(max_chars * 0.7)  # Chinese chars are wider

    return max(10, max_chars)  # Minimum 10 chars

def create_text_overlay_clips(text_content, video_width=1080, video_height=1920, video_duration=None):
    """Create text overlay clips from bodytext content with wipe down animation"""
    # Split text into lines
    text_lines = text_content.strip().split('\n')
    text_lines = [line.strip() for line in text_lines if line.strip()]

    # Font settings
    font_size = 48
    font_color = "white"
    bg_color = (0, 0, 0)  # Black background
    bg_opacity = 0.7

    # Use specified font for Chinese text
    font_name = "Hiragino Sans GB"

    # Calculate line height and positioning
    line_height = font_size + 10
    total_text_height = len(text_lines) * line_height

    # Start position for text block (centered vertically)
    start_y = (video_height - total_text_height) // 2

    text_clips = []
    bg_clips = []

    # First pass: create all text clips to calculate total dimensions
    for i, line_text in enumerate(text_lines):
        if not line_text.strip():
            continue

        # Calculate maximum text width
        max_text_width = int(video_width * 0.8)

        # Split long lines if necessary
        max_chars_per_line = calculate_safe_max_chars(line_text, max_text_width)
        line_parts = split_long_subtitle_text(line_text, max_chars_per_line)

        for j, part_text in enumerate(line_parts):
            # Create text clip
            text_clip = TextClip(
                font_name,
                part_text,
                font_size=font_size,
                color=font_color,
                stroke_color="black",
                stroke_width=1,
                size=(max_text_width, None),
                method="caption",
                text_align="center",
                transparent=True,
            )

            # Position the text line
            line_index = i + j
            y_position = start_y + line_index * line_height
            text_clip = text_clip.with_position(("center", y_position))

            text_clips.append(text_clip)

    # Create single background clip for all text lines
    if text_clips:
        max_text_width = max(clip.w for clip in text_clips)
        bg_width = int(max_text_width + 20)
        bg_height = int(total_text_height + 10)  # Cover all lines plus padding
        bg_x = (video_width - bg_width) // 2  # Center horizontally
        bg_y = start_y - 10  # Offset above first text line

        bg_clip = (
            ColorClip(size=(bg_width, bg_height), color=bg_color)
            .with_opacity(bg_opacity)
            .with_position((bg_x, bg_y))
        )
        bg_clips.append(bg_clip)

    # Apply sequential wipe down animation timing to text clips
    timed_text_clips = []

    # Animation settings for wipe down effect
    line_delay = 0.5  # Delay between each line appearing (seconds)
    fade_duration = 0.3  # Fade in duration for each line (seconds)

    bodyTextStartAt = 0.0  # Start animation at beginning
    bodyTextDuration = video_duration if video_duration else 10.0

    for i, text_clip in enumerate(text_clips):
        # Calculate timing for downward erase animation
        # Each line appears with a delay, creating the wipe down effect
        line_start_time = bodyTextStartAt + i * line_delay
        line_end_time = bodyTextStartAt + bodyTextDuration

        # Apply fade in effect with proper timing
        timed_text_clip = text_clip.with_start(line_start_time).with_duration(
            line_end_time - line_start_time
        )
        timed_text_clip = timed_text_clip.with_effects([FadeIn(fade_duration)])

        timed_text_clips.append(timed_text_clip)

    # Apply timing to single background clip (background appears immediately)
    timed_bg_clips = []
    for bg_clip in bg_clips:
        timed_bg_clip = bg_clip.with_start(bodyTextStartAt).with_duration(
            bodyTextDuration
        )
        timed_bg_clips.append(timed_bg_clip)

    return timed_bg_clips + timed_text_clips

def main():
    # File paths
    bodytext_path = "/Users/lucas/dev/aivideo/vault/demo/c93eb33c-7b13-4d8d-aa3d-3335ffde1339/subtitle/bodytext.txt"
    video_path = "/Users/lucas/dev/aivideo/vault/public/media/sexygirl.mp4"
    output_path = "/Users/lucas/dev/aivideo/test_text_animation_output.mp4"

    # Check if input files exist
    if not os.path.exists(bodytext_path):
        print(f"Error: Bodytext file not found: {bodytext_path}")
        sys.exit(1)

    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)

    print("Reading text content from bodytext.txt...")
    with open(bodytext_path, 'r', encoding='utf-8') as f:
        text_content = f.read()

    print(f"Text content: {text_content[:100]}...")

    print("Loading video...")
    video_clip = VideoFileClip(video_path)

    print("Creating text overlay clips...")
    text_overlay_clips = create_text_overlay_clips(text_content, video_clip.w, video_clip.h, video_clip.duration)

    print(f"Created {len(text_overlay_clips)} text overlay clips")

    # Composite video with text overlays
    print("Compositing video with text...")
    final_clip = CompositeVideoClip([video_clip] + text_overlay_clips)

    # Ensure final clip has duration
    if not hasattr(final_clip, 'duration') or final_clip.duration is None:
        final_clip = final_clip.with_duration(video_clip.duration)

    print(f"Writing output video to: {output_path}")
    final_clip.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        fps=24,
        preset="fast",
        threads=4,
        ffmpeg_params=["-crf", "23", "-pix_fmt", "yuv420p"]
    )

    # Clean up
    final_clip.close()
    video_clip.close()
    for clip in text_overlay_clips:
        clip.close()

    print(f"✅ Text animation test completed! Output: {output_path}")

if __name__ == "__main__":
    main()
