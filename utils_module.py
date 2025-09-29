#!/usr/bin/env python3
"""
Utility functions for the AI Video Generator
"""

import os
import subprocess
import numpy as np
from moviepy import TextClip, ColorClip, CompositeVideoClip
from pathlib import Path


def contains_chinese(text):
    """Check if text contains Chinese characters"""
    if not text:
        return False

    # Chinese character ranges (including common CJK characters)
    chinese_ranges = [
        (0x4E00, 0x9FFF),  # CJK Unified Ideographs (Common Chinese)
        (0x3400, 0x4DBF),  # CJK Unified Ideographs Extension A
        (0x20000, 0x2A6DF),  # CJK Unified Ideographs Extension B
        (0x2A700, 0x2B73F),  # CJK Unified Ideographs Extension C
        (0x2B740, 0x2B81F),  # CJK Unified Ideographs Extension D
        (0x2B820, 0x2CEAF),  # CJK Unified Ideographs Extension E
        (0x3300, 0x33FF),  # CJK Compatibility
        (0xFE30, 0xFE4F),  # CJK Compatibility Forms
        (0xF900, 0xFAFF),  # CJK Compatibility Ideographs
        (0x2F800, 0x2FA1F),  # CJK Compatibility Ideographs Supplement
        (0x3100, 0x312F),  # Bopomofo
        (0x31A0, 0x31BF),  # Bopomofo Extended
        (0x3040, 0x309F),  # Hiragana
        (0x30A0, 0x30FF),  # Katakana
        (0xAC00, 0xD7AF),  # Hangul Syllables
    ]

    chinese_chars = []
    for char in text:
        char_code = ord(char)
        for start, end in chinese_ranges:
            if start <= char_code <= end:
                chinese_chars.append(char)
                break

    if chinese_chars:
        # print(f">>>Chinese characters detected: {chinese_chars}")
        return True
    return False


def calculate_display_length(text):
    """Calculate display length where 2 English chars = 1 Chinese char"""
    chinese_chars = 0
    english_chars = 0

    for char in text:
        if "\u4e00" <= char <= "\u9fff":  # Chinese character
            chinese_chars += 1
        elif char.isalpha() and char.isascii():  # English letter
            english_chars += 1
        # Ignore spaces and punctuation for length calculation

    # Calculate: Chinese chars count as 1, English chars count as 0.5 each
    # Total should not exceed 20 (equivalent to 20 Chinese chars)
    return chinese_chars + (english_chars / 2)


def count_chinese_characters(text):
    """Count Chinese characters in text"""
    count = 0
    for char in text:
        if "\u4e00" <= char <= "\u9fff":  # Unicode range for Chinese characters
            count += 1
    return count


def split_by_chinese_count(text, max_length):
    """Split text by length calculation where 2 English chars = 1 Chinese char"""
    if not text:
        return []

    chunks = []
    current_chunk = ""
    current_length = 0

    for char in text:
        # Calculate length contribution of this character
        if "\u4e00" <= char <= "\u9fff":  # Chinese character
            char_length = 1
        elif char.isalpha() and char.isascii():  # English letter
            char_length = 0.5
        else:  # Punctuation, numbers, spaces - don't count towards length
            char_length = 0

        # Check if adding this character would exceed the limit
        if current_length + char_length > max_length and current_chunk:
            # Save current chunk and start new one
            chunks.append(current_chunk)
            current_chunk = char
            current_length = char_length
        else:
            # Add to current chunk
            current_chunk += char
            current_length += char_length

    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def split_mixed_text(text, max_length=20):
    """Split mixed Chinese-English text at appropriate boundaries"""
    if not should_split_mixed_text(text, max_length):
        return [text]

    # Try to split at spaces first (between English words)
    words = text.split()
    if len(words) <= 1:
        return [text]  # Can't split

    chunks = []
    current_chunk = ""
    current_length = 0

    for word in words:
        # Calculate length of this word
        word_length = calculate_display_length(word)
        space_length = calculate_display_length(" ") if current_chunk else 0

        if current_length + space_length + word_length <= max_length:
            # Add word to current chunk
            if current_chunk:
                current_chunk += " " + word
                current_length += space_length + word_length
            else:
                current_chunk = word
                current_length += word_length
        else:
            # Start new chunk
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = word
            current_length = word_length

    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def should_split_mixed_text(text, max_length=20):
    """Check if mixed Chinese-English text should be split based on length calculation"""
    return calculate_display_length(text) > max_length


def clean_punctuation(text):
    """Clean punctuation from text while preserving periods, question marks, and exclamation marks"""
    if not text:
        return text

    # Extract and preserve periods, question marks and exclamation marks throughout the text
    preserved_marks = []
    text_without_marks = ""

    i = 0
    while i < len(text):
        if text[i] in "。！？!?":
            preserved_marks.append((i, text[i]))  # Store position and mark
        else:
            text_without_marks += text[i]
        i += 1

    # Punctuation to remove (all punctuation except periods, question marks, and exclamation marks)
    punctuation_to_remove = (
        "，、；：\"\"''()（）【】《》<>》>——・•·…—–~@#$%^&*_+=|\\\\/{}.,;:[]"
    )

    # Remove all occurrences of forbidden punctuation
    cleaned = text_without_marks
    for char in punctuation_to_remove:
        cleaned = cleaned.replace(char, "")

    # Remove extra whitespace
    cleaned = " ".join(cleaned.split())

    # Re-insert the preserved periods, question marks, and exclamation marks
    # Adjust positions based on removed characters
    result = ""
    cleaned_index = 0
    for orig_pos, mark in preserved_marks:
        # Add text up to this position
        while cleaned_index < len(cleaned) and cleaned_index < orig_pos:
            result += cleaned[cleaned_index]
            cleaned_index += 1

        # Add the preserved mark
        result += mark

    # Add remaining cleaned text
    result += cleaned[cleaned_index:]

    return result


def split_by_punctuation(text, punctuation_char):
    """Split text by punctuation character, preserving the punctuation in the result"""
    parts = []
    current_part = ""

    for char in text:
        current_part += char
        if char == punctuation_char:
            parts.append(current_part)
            current_part = ""

    # Add remaining part
    if current_part.strip():
        parts.append(current_part)

    return parts


def split_by_em_dash(text):
    """Split text by em dash (——), handling it as a single unit"""
    parts = []
    current_part = ""
    i = 0

    while i < len(text):
        if i + 1 < len(text) and text[i] == "—" and text[i + 1] == "—":
            # Found em dash
            current_part += "——"  # Add the em dash to current part
            parts.append(current_part)
            current_part = ""
            i += 2  # Skip both characters
        else:
            current_part += text[i]
            i += 1

    # Add remaining part
    if current_part.strip():
        parts.append(current_part)

    return parts


def split_by_punctuation_marks(text):
    """Split text by punctuation marks (preserving question marks and exclamation marks)"""
    if not text:
        return []

    # Chinese punctuation marks to split by (excluding question marks and exclamation marks)
    punctuation_marks = '，。、；：""\'\'()（）【】《》<>——・•·…—–'

    parts = [text]
    for mark in punctuation_marks:
        new_parts = []
        for part in parts:
            sub_parts = part.split(mark)
            # Filter out empty parts but preserve order
            sub_parts = [p for p in sub_parts if p.strip()]
            new_parts.extend(sub_parts)
        parts = new_parts

    # Additional split: separate content after question marks and exclamation marks
    final_parts = []
    for part in parts:
        # Look for question marks or exclamation marks that are not at the end
        split_needed = False
        for i, char in enumerate(part):
            if char in "！？!?" and i < len(part) - 1:  # Not at the end
                # Split before and after the question/exclamation mark
                before = part[: i + 1]  # Include the question/exclamation mark
                after = part[i + 1 :].strip()  # Content after
                if before.strip():
                    final_parts.append(before.strip())
                if after.strip():
                    final_parts.append(after.strip())
                split_needed = True
                break

        if not split_needed:
            final_parts.append(part)

    return final_parts


def split_by_length(subtitle):
    """Split subtitle by character/word count as last resort"""
    max_length = 25 if contains_chinese(subtitle) else 40

    if len(subtitle) <= max_length:
        return [subtitle]

    if contains_chinese(subtitle):
        # For Chinese, split at word boundaries or character count
        mid_point = len(subtitle) // 2
        # Try to find a good split point
        for i in range(mid_point, max(0, mid_point - 10), -1):
            if i < len(subtitle) - 1:
                return [subtitle[:i], clean_punctuation(subtitle[i:].strip())]
        # Fallback
        return [
            subtitle[:max_length],
            clean_punctuation(subtitle[max_length:].strip()),
        ]
    else:
        # For English, split by word boundaries
        words = subtitle.split()
        if len(words) <= 8:  # If not too many words, keep as is
            return [subtitle]

        # Try to find a good split point
        mid_point = len(words) // 2
        for i in range(mid_point, max(0, mid_point - 3), -1):
            first_part = " ".join(words[:i])
            second_part = " ".join(words[i:])
            if len(first_part) >= 5 and len(second_part) >= 5:
                return [
                    clean_punctuation(first_part),
                    clean_punctuation(second_part),
                ]

        # Fallback
        return [subtitle]


def split_long_subtitle_text(text, max_length=14):
    """Split long subtitle text into multiple lines for mobile display"""
    # First, check if text needs splitting based on visual width rather than character count
    if len(text) <= max_length:
        return [text]

    # For Chinese text, use a more conservative approach
    if contains_chinese(text):
        max_length = 12  # Chinese characters are wider

    # Try to split at natural break points
    break_points = [
        "，",
        "。",
        "！",
        "？",
        "、",
        "；",
        "：",
        " ",
        "的",
        "和",
        "与",
        "及",
    ]

    for break_char in break_points:
        if break_char in text:
            parts = text.split(break_char)
            if len(parts) > 1:
                result = []
                current_line = ""
                for part in parts:
                    # Check if adding this part would exceed the limit
                    test_line = (
                        current_line + (break_char if current_line else "") + part
                    )
                    if len(test_line) <= max_length:
                        if current_line:
                            current_line += break_char + part
                        else:
                            current_line = part
                    else:
                        # Current line is full, add to result
                        if current_line:
                            result.append(current_line)
                        # Start new line with current part
                        current_line = part
                        # If the part itself is too long, split it further
                        if len(current_line) > max_length:
                            # Split the part into chunks
                            for i in range(0, len(current_line), max_length):
                                result.append(current_line[i : i + max_length])
                            current_line = ""
                if current_line:
                    result.append(current_line)

                # Validate all lines are within limits
                result = [line for line in result if line.strip()]
                if all(len(line) <= max_length for line in result):
                    return result

    # If no natural break points, split by character count
    lines = []
    for i in range(0, len(text), max_length):
        lines.append(text[i : i + max_length])
    return lines


def calculate_safe_max_chars(text, max_width_pixels):
    """Calculate safe maximum characters based on character types"""
    if not text:
        return 20  # Default fallback

    # Count character types
    chinese_count = sum(1 for char in text if contains_chinese(char))
    english_count = sum(
        1 for char in text if char.isalpha() and not contains_chinese(char)
    )
    digit_count = sum(1 for char in text if char.isdigit())

    # Calculate character width multiplier
    # Chinese characters are ~2x wider than English characters
    char_width_sum = chinese_count * 2 + english_count + digit_count * 1.5
    avg_char_width = char_width_sum / len(text) if text else 1.5

    # Estimate safe character count based on pixel width
    # Assuming average character width of ~12 pixels for English
    safe_chars = int(max_width_pixels / (12 * avg_char_width))

    return min(safe_chars, 12 if chinese_count > 0 else 14)


def estimate_speaking_time(text):
    """Estimate speaking time for text based on linguistic analysis"""
    if not text:
        return 1.0  # Minimum duration

    # Count different types of characters
    chinese_chars = sum(1 for char in text if contains_chinese(char))
    english_words = len(
        [word for word in text.split() if not contains_chinese(word)]
    )
    digits = sum(1 for char in text if char.isdigit())
    punctuation = sum(1 for char in text if char in '，。！？；：""（）【】《》')

    # Fixed timing calculation - more reasonable limits
    # Chinese characters: ~0.25 seconds each (faster pace)
    # English words: ~0.2 seconds each
    # Digits: ~0.3 seconds each
    # Punctuation: minimal pause time

    chinese_time = chinese_chars * 0.25
    english_time = english_words * 0.2
    digit_time = digits * 0.3
    punctuation_time = punctuation * 0.1

    # Base time from content
    base_time = chinese_time + english_time + digit_time + punctuation_time

    # Much more reasonable bounds - prevent any single subtitle from dominating
    # Maximum 8 seconds per subtitle, minimum 2 seconds
    estimated_time = max(2.0, min(base_time, 8.0))

    return estimated_time


def get_chinese_compatible_font(default_font="Arial"):
    """Get a font that supports Chinese characters"""
    # List of Chinese-compatible fonts, in order of preference
    chinese_fonts = [
        # Cross-platform Unicode fonts (verified working for rendering)
        "Arial-Unicode-MS",  # Cross-platform Unicode - WORKING for rendering
        "Lucida Sans Unicode",  # Cross-platform Unicode
        # macOS Chinese fonts (detected but rendering issues)
        "Heiti SC",  # macOS Chinese simplified - detected but rendering issues
        "Heiti TC",  # macOS Chinese traditional - detected but rendering issues
        "Noto Sans SC",  # macOS Noto Sans Chinese - detected but rendering issues
        "STHeiti Medium",  # macOS Chinese medium
        "STHeiti Light",  # macOS Chinese light
        # Additional macOS fonts
        "PingFang SC",  # macOS system font
        "PingFang HK",  # macOS Hong Kong variant
        "PingFang TC",  # macOS Taiwan variant
        "Hiragino Sans GB",  # macOS Chinese simplified
        # Windows fonts
        "Microsoft YaHei",  # Windows Chinese font
        "SimSun",  # Windows Chinese simplified
        "SimHei",  # Windows Chinese Simplified
        # Linux/open source fonts
        "Noto Sans CJK SC",  # Linux Noto Sans
        "WenQuanYi Micro Hei",  # Linux Chinese font
        "AR PL UMing CN",  # Linux Chinese font
        # Try with underscores instead of hyphens (some systems use this format)
        "Heiti_SC",
        "Heiti_TC",
        "Noto_Sans_SC",
        "PingFang_SC",
        "Arial_Unicode_MS",
        "Lucida_Sans_Unicode",
        default_font,  # Fallback to default
    ]

    # Try each font until we find one that works
    for font in chinese_fonts:
        try:
            # Test if the font can render Chinese characters with proper rendering check
            test_text = "测试中文字体"
            test_clip = TextClip(
                font,
                test_text,
                font_size=12,
                color="white",
                stroke_color="black",
                stroke_width=1,
                size=(200, 50),
                method="label",
            )

            # Create a black background to test rendering
            bg = ColorClip(size=(200, 50), color=(0, 0, 0))
            composite = CompositeVideoClip([bg, test_clip.with_position("center")])

            # Get a frame to verify actual rendering
            test_frame = composite.get_frame(0)

            # Check if text was actually rendered (not just black background)
            text_rendered = not (test_frame == 0).all()

            # Clean up
            test_clip.close()
            bg.close()
            composite.close()

            if text_rendered:
                return font
            else:
                continue

        except Exception as font_error:
            # Also try with a simpler test to see if the font exists at all
            try:
                simple_test = TextClip(
                    font,
                    "Test",
                    font_size=12,
                    color="white",
                    stroke_color="black",
                    stroke_width=1,
                    method="label",
                )
                simple_test.close()
            except Exception as e2:
                continue

    # If none of the predefined fonts work, try to find Chinese fonts in system
    system_font = find_chinese_font_in_system()
    if system_font:
        return system_font

    # If no Chinese font works, try the default font
    try:
        test_clip = TextClip(
            default_font,
            "Test",
            font_size=12,
            color="white",
            stroke_color="black",
            stroke_width=1,
            method="label",
        )
        test_clip.close()
        return default_font
    except Exception as e:
        return None


def get_system_fonts():
    """Get available system fonts on macOS"""
    try:
        # Use system_profiler to get available fonts on macOS
        result = subprocess.run(
            ["system_profiler", "SPFontsDataType"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            font_lines = []
            for line in result.stdout.split("\n"):
                if "Font Name:" in line:
                    font_name = line.split("Font Name:")[1].strip()
                    font_lines.append(font_name)
            return font_lines
    except Exception as e:
        pass
    return []


def find_chinese_font_in_system():
    """Find Chinese fonts in system font list"""
    system_fonts = get_system_fonts()
    if not system_fonts:
        return None

    # Look for Chinese fonts in the system list
    chinese_keywords = [
        "PingFang",
        "Heiti",
        "STHeiti",
        "Hiragino",
        "Microsoft YaHei",
        "SimSun",
        "SimHei",
        "Noto Sans CJK",
        "WenQuanYi",
        "KaiTi",
        "FangSong",
    ]

    for font in system_fonts:
        for keyword in chinese_keywords:
            if keyword.lower() in font.lower():
                # Test if it works
                try:
                    test_clip = TextClip(
                        font,
                        "测试中文字体",
                        font_size=12,
                        color="white",
                        stroke_color="black",
                        stroke_width=1,
                        method="label",
                    )
                    test_clip.close()
                    return font
                except Exception as e:
                    continue

    return None