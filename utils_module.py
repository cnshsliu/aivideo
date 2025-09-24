#!/usr/bin/env python3
"""
Utilities Module for AI Video Generator
Damn, this contains all the damn utility functions! Don't mess with it!
"""

import os
import sys
import time
import logging
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
from datetime import datetime

class RecentLogHandler(logging.Handler):
    """Custom handler that maintains a single recent_log file with all console output"""

    def __init__(self, recent_log_file: Path):
        super().__init__()
        self.recent_log_file = recent_log_file
        # Ensure the directory exists
        self.recent_log_file.parent.mkdir(parents=True, exist_ok=True)
        # Clear the file at the start of each run
        if self.recent_log_file.exists():
            self.recent_log_file.unlink()

    def emit(self, record):
        """Emit a record to the recent log file"""
        try:
            msg = self.format(record)
            with open(self.recent_log_file, 'a', encoding='utf-8') as f:
                f.write(msg + '\n')
        except Exception:
            self.handleError(record)

class PrintCapture:
    """Class to capture print statements and redirect them to log"""

    def __init__(self, recent_log_file: Path):
        self.recent_log_file = recent_log_file
        self.original_stdout = sys.stdout

    def write(self, text):
        """Write to both stdout and recent log file"""
        # Write to original stdout
        self.original_stdout.write(text)
        self.original_stdout.flush()

        # Write to recent log file if it's not just whitespace
        if text.strip():
            try:
                with open(self.recent_log_file, 'a', encoding='utf-8') as f:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f'{timestamp} - PRINT - {text}')
            except Exception:
                pass  # Silently ignore errors to avoid breaking the application

    def flush(self):
        """Flush the original stdout"""
        self.original_stdout.flush()

    def close(self):
        """Close the capture and restore original stdout"""
        self.original_stdout.close()

def setup_logging(log_file: Path = None, level: str = "INFO") -> Tuple[logging.Logger, Path]:
    """Setup logging configuration with unified recent_log"""
    # Create logs directory if needed
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

    # Create recent_log file in the same directory
    recent_log_file = log_file.parent / "recent_log.log" if log_file else Path("recent_log.log")

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[]
    )

    # Get the root logger
    root_logger = logging.getLogger()

    # Clear existing handlers
    root_logger.handlers.clear()

    # Add file handler for timestamped log (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        root_logger.addHandler(file_handler)

    # Add recent log handler (single file for all console output)
    recent_handler = RecentLogHandler(recent_log_file)
    recent_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(recent_handler)

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(console_handler)

    # Redirect print statements to recent log
    print_capture = PrintCapture(recent_log_file)
    sys.stdout = print_capture

    return logging.getLogger(__name__), recent_log_file

def read_recent_log(project_folder: Path = None) -> Optional[str]:
    """Read the contents of the recent log file"""
    if project_folder:
        recent_log_file = project_folder / "logs" / "recent_log.log"
    else:
        recent_log_file = Path("recent_log.log")

    if recent_log_file.exists():
        try:
            with open(recent_log_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            pass
    return None

def clear_recent_log(project_folder: Path = None) -> bool:
    """Clear the recent log file"""
    if project_folder:
        recent_log_file = project_folder / "logs" / "recent_log.log"
    else:
        recent_log_file = Path("recent_log.log")

    try:
        if recent_log_file.exists():
            recent_log_file.unlink()
        return True
    except Exception:
        return False

def validate_file_exists(file_path: Union[str, Path], description: str = "file") -> bool:
    """Validate that a file exists"""
    path = Path(file_path)
    if not path.exists():
        logging.error(f"{description.capitalize()} not found: {path}")
        return False
    return True

def validate_directory_exists(dir_path: Union[str, Path], description: str = "directory", create: bool = False) -> bool:
    """Validate that a directory exists"""
    path = Path(dir_path)
    if not path.exists():
        if create:
            path.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created {description}: {path}")
            return True
        else:
            logging.error(f"{description.capitalize()} not found: {path}")
            return False
    return True

def validate_dependencies() -> Dict[str, bool]:
    """Check if required dependencies are available"""
    dependencies = {
        'ffmpeg': check_ffmpeg(),
        'python': check_python_version(),
        'moviepy': check_moviepy(),
        'numpy': check_numpy(),
        'requests': check_requests(),
        'websockets': check_websockets()
    }

    # Log dependency status
    for dep, status in dependencies.items():
        if status:
            logging.info(f"✓ {dep} is available")
        else:
            logging.warning(f"✗ {dep} is not available")

    return dependencies

def check_ffmpeg() -> bool:
    """Check if FFmpeg is available"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def check_python_version() -> bool:
    """Check Python version"""
    try:
        version = sys.version_info
        return version.major >= 3 and version.minor >= 8
    except:
        return False

def check_moviepy() -> bool:
    """Check if moviepy is available"""
    try:
        import moviepy
        return True
    except ImportError:
        return False

def check_numpy() -> bool:
    """Check if numpy is available"""
    try:
        import numpy
        return True
    except ImportError:
        return False

def check_requests() -> bool:
    """Check if requests is available"""
    try:
        import requests
        return True
    except ImportError:
        return False

def check_websockets() -> bool:
    """Check if websockets is available"""
    try:
        import websockets
        return True
    except ImportError:
        return False

def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.1f}s"

def format_file_size(size_bytes: int) -> str:
    """Format file size in bytes to human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"

def get_file_info(file_path: Union[str, Path]) -> Dict[str, Union[str, int, float]]:
    """Get file information"""
    path = Path(file_path)
    if not path.exists():
        return {}

    try:
        stat = path.stat()
        return {
            'name': path.name,
            'size': stat.st_size,
            'size_formatted': format_file_size(stat.st_size),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'extension': path.suffix.lower(),
            'is_video': path.suffix.lower() in {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'},
            'is_image': path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'},
            'is_audio': path.suffix.lower() in {'.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a'}
        }
    except Exception as e:
        logging.error(f"Error getting file info for {path}: {e}")
        return {}

def ensure_directory(path: Union[str, Path]) -> Path:
    """Ensure directory exists, create if necessary"""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def clean_filename(filename: str) -> str:
    """Clean filename by removing invalid characters"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def get_timestamp() -> str:
    """Get current timestamp string"""
    return time.strftime("%Y%m%d_%H%M%S")

def get_date_string() -> str:
    """Get current date string"""
    return time.strftime("%Y-%m-%d")

def split_long_text(text: str, max_length: int = 50) -> List[str]:
    """Split long text into multiple lines"""
    if len(text) <= max_length:
        return [text]

    # Try to split at word boundaries first
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        if len(current_line + " " + word) <= max_length:
            current_line += " " + word if current_line else word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    # If still too long, split by character
    if len(lines) == 1 and len(lines[0]) > max_length:
        lines = [text[i:i+max_length] for i in range(0, len(text), max_length)]

    return lines

def estimate_video_duration(file_path: Union[str, Path]) -> float:
    """Estimate video duration without loading full file"""
    try:
        # Use ffprobe if available
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', str(file_path)
        ], capture_output=True, text=True)

        if result.returncode == 0:
            return float(result.stdout.strip())

    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        pass

    return 0.0

def monitor_progress(current: int, total: int, description: str = "Processing") -> None:
    """Monitor and display progress"""
    if total == 0:
        return

    percentage = (current / total) * 100
    bar_length = 40
    filled_length = int(bar_length * current // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)

    print(f'\r{description}: |{bar}| {percentage:.1f}% ({current}/{total})', end='', flush=True)

    if current >= total:
        print()  # New line when complete

def retry_function(func, max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Retry function with exponential backoff"""
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e

                wait_time = delay * (backoff ** attempt)
                logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)

    return wrapper

def validate_environment_variables(required_vars: List[str]) -> Dict[str, bool]:
    """Validate required environment variables"""
    from dotenv import load_dotenv
    load_dotenv()

    results = {}
    for var in required_vars:
        value = os.getenv(var)
        results[var] = bool(value)

        if not value:
            logging.error(f"Missing environment variable: {var}")
        else:
            logging.info(f"✓ {var} is set")

    return results

def get_system_info() -> Dict[str, str]:
    """Get system information"""
    import platform

    return {
        'os': platform.system(),
        'os_version': platform.version(),
        'python_version': platform.python_version(),
        'architecture': platform.architecture()[0],
        'processor': platform.processor(),
        'hostname': platform.node()
    }

def create_backup(file_path: Union[str, Path], backup_dir: Union[str, Path] = None) -> Optional[Path]:
    """Create backup of a file"""
    source = Path(file_path)
    if not source.exists():
        return None

    if backup_dir is None:
        backup_dir = source.parent / "backups"

    backup_dir = Path(backup_dir)
    backup_dir.mkdir(exist_ok=True)

    timestamp = get_timestamp()
    backup_name = f"{source.stem}_backup_{timestamp}{source.suffix}"
    backup_path = backup_dir / backup_name

    try:
        import shutil
        shutil.copy2(source, backup_path)
        logging.info(f"Backup created: {backup_path}")
        return backup_path
    except Exception as e:
        logging.error(f"Failed to create backup: {e}")
        return None

def cleanup_old_files(directory: Union[str, Path], pattern: str = "*", max_age_days: int = 7) -> int:
    """Clean up old files in directory"""
    dir_path = Path(directory)
    if not dir_path.exists():
        return 0

    count = 0
    cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)

    for file_path in dir_path.glob(pattern):
        if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
            try:
                file_path.unlink()
                count += 1
                logging.info(f"Deleted old file: {file_path}")
            except Exception as e:
                logging.error(f"Failed to delete {file_path}: {e}")

    logging.info(f"Cleaned up {count} old files")
    return count

def check_disk_space(path: Union[str, Path], min_space_mb: int = 100) -> bool:
    """Check if there's enough disk space"""
    try:
        import shutil
        total, used, free = shutil.disk_usage(Path(path))
        free_mb = free // (1024 * 1024)
        return free_mb >= min_space_mb
    except Exception:
        return True  # Assume there's enough space if we can't check

def send_notification(message: str, title: str = "AI Video Generator") -> bool:
    """Send desktop notification (if supported)"""
    try:
        # Try different notification methods
        if sys.platform == 'darwin':  # macOS
            subprocess.run(['osascript', '-e', f'display notification "{message}" with title "{title}"'],
                         capture_output=True)
            return True
        elif sys.platform.startswith('linux'):  # Linux
            subprocess.run(['notify-send', title, message], capture_output=True)
            return True
        elif sys.platform == 'win32':  # Windows
            from windows_toasts import WindowsToaster, Toast
            toaster = WindowsToaster(title)
            toast = Toast()
            toast.text_fields = [message]
            toaster.show_toast(toast)
            return True

    except Exception as e:
        logging.debug(f"Notification not supported: {e}")

    return False

def estimate_speaking_time(text: str) -> float:
    """Estimate speaking time for text based on linguistic analysis"""
    if not text:
        return 1.0  # Minimum duration

    # Count different types of characters
    total_chars = len(text)
    chinese_chars = sum(1 for char in text if contains_chinese(char))
    english_words = len([word for word in text.split() if not contains_chinese(word)])
    digits = sum(1 for char in text if char.isdigit())
    punctuation = sum(1 for char in text if char in '，。！？；：""''（）【】《》')

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

def clean_and_validate_subtitle(subtitle: str) -> str:
    """Clean and validate a single subtitle to ensure it meets requirements"""
    # Remove extra whitespace
    cleaned = subtitle.strip()

    # Ensure it ends with proper punctuation (prefer period)
    if not cleaned.endswith('。') and not cleaned.endswith('！') and not cleaned.endswith('？'):
        cleaned += '。'

    # Clean any other punctuation issues while preserving sentence structure
    cleaned = clean_punctuation(cleaned)

    return cleaned

def remove_trailing_period(text: str) -> str:
    """Remove trailing period from text for display purposes"""
    if text.endswith('。'):
        return text[:-1]
    return text

def contains_chinese(text: str) -> bool:
    """Check if text contains Chinese characters"""
    if not text:
        return False

    # Chinese character ranges (including common CJK characters)
    chinese_ranges = [
        (0x4E00, 0x9FFF),    # CJK Unified Ideographs (Common Chinese)
        (0x3400, 0x4DBF),    # CJK Unified Ideographs Extension A
        (0x20000, 0x2A6DF),  # CJK Unified Ideographs Extension B
        (0x2A700, 0x2B73F),  # CJK Unified Ideographs Extension C
        (0x2B740, 0x2B81F),  # CJK Unified Ideographs Extension D
        (0x2B820, 0x2CEAF),  # CJK Unified Ideographs Extension E
        (0x3300, 0x33FF),    # CJK Compatibility
        (0xFE30, 0xFE4F),    # CJK Compatibility Forms
        (0xF900, 0xFAFF),    # CJK Compatibility Ideographs
        (0x2F800, 0x2FA1F),  # CJK Compatibility Ideographs Supplement
        (0x3100, 0x312F),    # Bopomofo
        (0x31A0, 0x31BF),    # Bopomofo Extended
        (0x3040, 0x309F),    # Hiragana
        (0x30A0, 0x30FF),    # Katakana
        (0xAC00, 0xD7AF),    # Hangul Syllables
    ]

    chinese_chars = []
    for char in text:
        char_code = ord(char)
        for start, end in chinese_ranges:
            if start <= char_code <= end:
                chinese_chars.append(char)
                break

    if chinese_chars:
        print(f"Chinese characters detected: {chinese_chars}")
        return True
    return False

def split_long_subtitle_text(text: str, max_length: int = 14) -> List[str]:
    """Split long subtitle text into multiple lines for mobile display"""
    # First, check if text needs splitting based on visual width rather than character count
    if len(text) <= max_length:
        return [text]

    # For Chinese text, use a more conservative approach
    if contains_chinese(text):
        max_length = 12  # Chinese characters are wider

    # Try to split at natural break points
    break_points = ['，', '。', '！', '？', '、', '；', '：', ' ', '的', '和', '与', '及']

    for break_char in break_points:
        if break_char in text:
            parts = text.split(break_char)
            if len(parts) > 1:
                result = []
                current_line = ""
                for part in parts:
                    # Check if adding this part would exceed the limit
                    test_line = current_line + (break_char if current_line else "") + part
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
                                result.append(current_line[i:i+max_length])
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
        lines.append(text[i:i+max_length])
    return lines

def calculate_safe_max_chars(text: str, max_width_pixels: int) -> int:
    """Calculate safe maximum characters based on character types"""
    if not text:
        return 20  # Default fallback

    # Count character types
    chinese_count = sum(1 for char in text if contains_chinese(char))
    english_count = sum(1 for char in text if char.isalpha() and not contains_chinese(char))
    digit_count = sum(1 for char in text if char.isdigit())

    # Calculate character width multiplier
    # Chinese characters are ~2x wider than English characters
    char_width_sum = chinese_count * 2 + english_count + digit_count * 1.5
    avg_char_width = char_width_sum / len(text) if text else 1.5

    # Estimate safe character count based on pixel width
    # Assuming average character width of ~12 pixels for English
    safe_chars = int(max_width_pixels / (12 * avg_char_width))

    return min(safe_chars, 12 if chinese_count > 0 else 14)

def get_chinese_compatible_font(default_font: str = 'Arial', logger=None) -> Optional[str]:
    """Get a font that supports Chinese characters"""
    from moviepy.editor import TextClip, ColorClip, CompositeVideoClip

    # List of Chinese-compatible fonts, in order of preference
    chinese_fonts = [
        # Cross-platform Unicode fonts (verified working for rendering)
        'Arial-Unicode-MS',  # Cross-platform Unicode - WORKING for rendering
        'Lucida Sans Unicode',  # Cross-platform Unicode

        # macOS Chinese fonts (detected but rendering issues)
        'Heiti SC',  # macOS Chinese simplified - detected but rendering issues
        'Heiti TC',  # macOS Chinese traditional - detected but rendering issues
        'Noto Sans SC',  # macOS Noto Sans Chinese - detected but rendering issues
        'STHeiti Medium',  # macOS Chinese medium
        'STHeiti Light',  # macOS Chinese light

        # Additional macOS fonts
        'PingFang SC',  # macOS system font
        'PingFang HK',  # macOS Hong Kong variant
        'PingFang TC',  # macOS Taiwan variant
        'Hiragino Sans GB',  # macOS Chinese simplified

        # Windows fonts
        'Microsoft YaHei',  # Windows Chinese font
        'SimSun',  # Windows Chinese simplified
        'SimHei',  # Windows Chinese Simplified

        # Linux/open source fonts
        'Noto Sans CJK SC',  # Linux Noto Sans
        'WenQuanYi Micro Hei',  # Linux Chinese font
        'AR PL UMing CN',  # Linux Chinese font

        # Try with underscores instead of hyphens (some systems use this format)
        'Heiti_SC',
        'Heiti_TC',
        'Noto_Sans_SC',
        'PingFang_SC',
        'Arial_Unicode_MS',
        'Lucida_Sans_Unicode',

        default_font  # Fallback to default
    ]

    # Try each font until we find one that works
    for font in chinese_fonts:
        try:
            if logger:
                logger.info(f"Testing font: {font}")

            # Test if the font can render Chinese characters with proper rendering check
            test_text = "测试中文字体"
            test_clip = TextClip(
                test_text,
                fontsize=12,
                color='white',
                font=font,
                stroke_color='black',
                stroke_width=1,
                size=(200, 50)
            )

            # Create a black background to test rendering
            bg = ColorClip(size=(200, 50), color=(0, 0, 0))
            composite = CompositeVideoClip([bg, test_clip.set_position('center')])

            # Get a frame to verify actual rendering
            test_frame = composite.get_frame(0)

            # Check if text was actually rendered (not just black background)
            text_rendered = not (test_frame == 0).all()

            # Clean up
            test_clip.close()
            bg.close()
            composite.close()

            if text_rendered:
                if logger:
                    logger.info(f"SUCCESS: Font {font} can properly render Chinese characters!")
                return font
            else:
                if logger:
                    logger.debug(f"Font {font} exists but doesn't render Chinese properly")
                continue

        except Exception as font_error:
            if logger:
                logger.debug(f"Font {font} failed Chinese test: {font_error}")
            # Also try with a simpler test to see if the font exists at all
            try:
                simple_test = TextClip(
                    "Test",
                    fontsize=12,
                    color='white',
                    font=font,
                    stroke_color='black',
                    stroke_width=1
                )
                simple_test.close()
                if logger:
                    logger.debug(f"Font {font} exists but can't render Chinese")
            except Exception as e2:
                if logger:
                    logger.debug(f"Font {font} doesn't exist at all: {e2}")

    if logger:
        logger.error(f"No Chinese-compatible font found. Default font {default_font} failed.")

    try:
        # Try the default font as a last resort
        test_clip = TextClip(
            "Test",
            fontsize=12,
            color='white',
            font=default_font,
            stroke_color='black',
            stroke_width=1
        )
        test_clip.close()
        if logger:
            logger.info(f"Using default font {default_font} as fallback")
        return default_font
    except Exception as e:
        if logger:
            logger.error(f"Even default font {default_font} failed: {e}")
        return None

def get_system_fonts(logger=None) -> List[str]:
    """Get available system fonts on macOS"""
    import subprocess
    try:
        # Use system_profiler to get available fonts on macOS
        result = subprocess.run(['system_profiler', 'SPFontsDataType'],
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            font_lines = []
            for line in result.stdout.split('\n'):
                if 'Font Name:' in line:
                    font_name = line.split('Font Name:')[1].strip()
                    font_lines.append(font_name)
            return font_lines
    except Exception as e:
        if logger:
            logger.warning(f"Could not get system fonts: {e}")
    return []

def find_chinese_font_in_system(logger=None) -> Optional[str]:
    """Find Chinese fonts in system font list"""
    from moviepy.editor import TextClip

    system_fonts = get_system_fonts(logger)
    if not system_fonts:
        return None

    # Look for Chinese fonts in the system list
    chinese_keywords = ['PingFang', 'Heiti', 'STHeiti', 'Hiragino', 'Microsoft YaHei',
                      'SimSun', 'SimHei', 'Noto Sans CJK', 'WenQuanYi', 'KaiTi', 'FangSong']

    for font in system_fonts:
        for keyword in chinese_keywords:
            if keyword.lower() in font.lower():
                if logger:
                    logger.info(f"Found Chinese font in system: {font}")
                # Test if it works
                try:
                    test_clip = TextClip(
                        "测试中文字体",
                        fontsize=12,
                        color='white',
                        font=font,
                        stroke_color='black',
                        stroke_width=1
                    )
                    test_clip.close()
                    return font
                except Exception as e:
                    if logger:
                        logger.debug(f"System font {font} failed test: {e}")
                    continue

    return None

def clean_punctuation(text: str) -> str:
    """Clean punctuation issues while preserving sentence structure"""
    # Remove excessive punctuation
    cleaned = re.sub(r'[。！？]{2,}', '。', text)
    cleaned = re.sub(r'[，]{2,}', '，', cleaned)
    cleaned = re.sub(r'[""]{2,}', '"', cleaned)

    # Ensure proper spacing around punctuation (for mixed text)
    cleaned = re.sub(r'([a-zA-Z])，', r'\1, ', cleaned)
    cleaned = re.sub(r'([a-zA-Z])。', r'\1. ', cleaned)
    cleaned = re.sub(r'([a-zA-Z])！', r'\1! ', cleaned)
    cleaned = re.sub(r'([a-zA-Z])？', r'\1? ', cleaned)

    # Clean up extra spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    return cleaned

def clean_punctuation_complex(text: str) -> str:
    """Clean punctuation from text while preserving periods, question marks, and exclamation marks"""
    if not text:
        return text

    # Extract and preserve periods, question marks, and exclamation marks throughout the text
    preserved_marks = []
    text_without_marks = ""

    i = 0
    while i < len(text):
        if text[i] in '。！？!?':
            preserved_marks.append((i, text[i]))  # Store position and mark
        else:
            text_without_marks += text[i]
        i += 1

    # Punctuation to remove (all punctuation except periods, question marks, and exclamation marks)
    punctuation_to_remove = '，、；：""\'\'()（）【】《》<>》>——・•·…—–~@#$%^&*_+=|\\/{}.,;:[]'

    # Remove all occurrences of forbidden punctuation
    cleaned = text_without_marks
    for char in punctuation_to_remove:
        cleaned = cleaned.replace(char, '')

    # Remove extra whitespace
    cleaned = ' '.join(cleaned.split())

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