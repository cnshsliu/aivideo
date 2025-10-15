#!/usr/bin/env python3
"""
Standalone script to process text with downward erase animation on black background
"""

import os
import sys
from pathlib import Path
from moviepy import TextClip, CompositeVideoClip, ColorClip, concatenate_videoclips, VideoFileClip
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

def create_downward_erase_animation(text_content, video_path=None, duration=10.0):
    """Create downward erase animation on video background"""

    # Load video background if provided
    if video_path and os.path.exists(video_path):
        background_clip = VideoFileClip(video_path)
        video_width, video_height = background_clip.w, background_clip.h
        # Trim or loop video to match duration
        if background_clip.duration < duration:
            # Loop the video if it's shorter than desired duration
            num_loops = int(duration // background_clip.duration) + 1
            background_clip = concatenate_videoclips([background_clip] * num_loops).subclipped(0, duration)
        else:
            # Trim video if it's longer
            background_clip = background_clip.subclipped(0, duration)
    else:
        # Fallback to black background if no video provided
        video_width, video_height = 1080, 1920
        background_clip = ColorClip(size=(video_width, video_height), color=(0, 0, 0)).with_duration(duration)

    # Split text into lines
    text_lines = text_content.strip().split('\n')
    text_lines = [line.strip() for line in text_lines if line.strip()]

    # Font settings
    font_size = 48
    font_color = "white"

    # Use specified font for Chinese text
    font_name = "Hiragino Sans GB"

    # Calculate line height and positioning
    line_height = font_size + 10
    total_text_height = len(text_lines) * line_height

    # Start position for text block (centered vertically)
    start_y = (video_height - total_text_height) // 2

    # Calculate timing for each line
    total_lines = len(text_lines)
    if total_lines == 0:
        return background_clip

    # Animation settings for downward erase effect
    line_delay = duration / total_lines  # Delay between each line appearing
    line_display_duration = duration - (total_lines - 1) * 0.5  # How long each line stays visible
    fade_duration = 0.3  # seconds to fade in each line

    all_clips = [background_clip]  # Start with background

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

            # Calculate timing for downward erase animation
            # Each line appears with a delay, creating the downward effect
            line_start_time = i * 0.5  # 0.5 second delay between lines
            line_end_time = duration  # Each line stays until the end

            # Apply fade in effect with proper timing
            text_clip = text_clip.with_start(line_start_time).with_duration(line_end_time - line_start_time)
            text_clip = text_clip.with_effects([FadeIn(fade_duration)])

            all_clips.append(text_clip)

    # Composite all clips
    final_clip = CompositeVideoClip(all_clips)

    return final_clip

def create_alternating_erase_animation(text_content, video_width=1080, video_height=1920, duration=10.0):
    """Create alternating erase animation (lines appear and disappear)"""

    # Split text into lines
    text_lines = text_content.strip().split('\n')
    text_lines = [line.strip() for line in text_lines if line.strip()]

    # Font settings
    font_size = 48
    font_color = "white"
    bg_color = (0, 0, 0)  # Black background

    # Use specified font for Chinese text
    font_name = "Hiragino Sans GB"

    # Calculate line height and positioning
    line_height = font_size + 10
    total_text_height = len(text_lines) * line_height

    # Start position for text block (centered vertically)
    start_y = (video_height - total_text_height) // 2

    # Create black background clip
    background_clip = ColorClip(size=(video_width, video_height), color=bg_color).with_duration(duration)

    # Calculate timing for each line
    total_lines = len(text_lines)
    if total_lines == 0:
        return background_clip

    # Each line has appear/disappear cycle
    cycle_duration = duration / total_lines
    appear_duration = cycle_duration * 0.6  # 60% of cycle time visible
    disappear_duration = cycle_duration * 0.4  # 40% of cycle time fading out

    all_clips = [background_clip]  # Start with background

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

            # Calculate timing for this line
            cycle_start = i * cycle_duration
            appear_start = cycle_start
            disappear_start = cycle_start + appear_duration

            # Create appear clip
            appear_clip = text_clip.with_start(appear_start).with_duration(appear_duration)
            appear_clip = appear_clip.with_effects([FadeIn(0.2)])

            # Create disappear clip (fade out)
            disappear_clip = text_clip.with_start(disappear_start).with_duration(disappear_duration)
            disappear_clip = disappear_clip.with_effects([FadeOut(0.2)])

            all_clips.append(appear_clip)
            all_clips.append(disappear_clip)

    # Composite all clips
    final_clip = CompositeVideoClip(all_clips)

    return final_clip

def main():
    # File paths
    bodytext_path = "/Users/lucas/dev/aivideo/vault/demo/c93eb33c-7b13-4d8d-aa3d-3335ffde1339/subtitle/bodytext.txt"
    video_path = "/Users/lucas/dev/aivideo/vault/public/media/sexygirl.mp4"
    output_path = "/Users/lucas/dev/aivideo/text_animation_output.mp4"

    # Check if input files exist
    if not os.path.exists(bodytext_path):
        print(f"Error: Bodytext file not found: {bodytext_path}")
        sys.exit(1)

    print("Reading text content from bodytext.txt...")
    with open(bodytext_path, 'r', encoding='utf-8') as f:
        text_content = f.read()

    print(f"Text content: {text_content[:100]}...")

    # Choose animation type
    animation_type = "downward_erase"  # Options: "downward_erase", "alternating"

    print(f"Creating {animation_type} animation...")

    if animation_type == "downward_erase":
        final_clip = create_downward_erase_animation(text_content, video_path=video_path, duration=8.0)
    elif animation_type == "alternating":
        final_clip = create_alternating_erase_animation(text_content, duration=8.0)
    else:
        print(f"Unknown animation type: {animation_type}")
        sys.exit(1)

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

    print(f"✅ Text animation completed! Output: {output_path}")
    print(f"Animation type: {animation_type}")

if __name__ == "__main__":
    main()
