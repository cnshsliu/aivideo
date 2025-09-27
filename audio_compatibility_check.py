#!/usr/bin/env python3
"""
Audio Codec Compatibility Checker
Check if video files have audio streams compatible with AAC codec
"""

import subprocess
import json
import sys
from pathlib import Path

def check_audio_codec_compatibility(video_path):
    """Check if a video file has audio streams compatible with AAC codec"""

    print(f"🔍 Checking audio compatibility for: {video_path}")

    if not Path(video_path).exists():
        print(f"❌ File does not exist: {video_path}")
        return False

    try:
        # Use ffprobe to get detailed stream information
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(video_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        video_info = json.loads(result.stdout)

        print(f"📁 Format: {video_info.get('format', {}).get('format_name', 'unknown')}")

        # Find audio streams
        audio_streams = [stream for stream in video_info.get('streams', [])
                        if stream.get('codec_type') == 'audio']

        if not audio_streams:
            print("ℹ️  No audio streams found (silent video)")
            return True  # Silent videos are compatible

        print(f"🔊 Found {len(audio_streams)} audio stream(s)")

        compatible = True

        for i, stream in enumerate(audio_streams):
            codec_name = stream.get('codec_name', 'unknown')
            codec_type = stream.get('codec_type', 'unknown')
            sample_rate = stream.get('sample_rate', 'unknown')
            channels = stream.get('channels', 'unknown')

            print(f"\n🎵 Audio Stream {i + 1}:")
            print(f"   Codec: {codec_name}")
            print(f"   Type: {codec_type}")
            print(f"   Sample Rate: {sample_rate} Hz")
            print(f"   Channels: {channels}")

            # Check compatibility with AAC
            if codec_name.lower() in ['aac', 'mp3', 'mp2', 'ac3', 'eac3', 'flac', 'alac', 'pcm_s16le', 'pcm_s24le', 'pcm_s32le']:
                print(f"   ✅ {codec_name} is compatible with AAC (can be converted)")
            else:
                print(f"   ⚠️  {codec_name} may have compatibility issues with AAC")
                compatible = False

            # Check sample rate compatibility
            if sample_rate != 'unknown':
                try:
                    sr = int(sample_rate)
                    if sr in [44100, 48000, 22050, 24000, 16000]:
                        print(f"   ✅ Sample rate {sr} Hz is standard")
                    else:
                        print(f"   ⚠️  Sample rate {sr} Hz is non-standard but usually convertible")
                except ValueError:
                    print(f"   ⚠️  Invalid sample rate: {sample_rate}")

        # Test actual conversion capability
        print(f"\n🧪 Testing AAC conversion...")

        # Create a temporary command to test AAC conversion
        test_cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-c:a", "aac",
            "-b:a", "192k",
            "-f", "null",
            "-"  # Output to null (just test)
        ]

        try:
            test_result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
            if test_result.returncode == 0:
                print("✅ AAC conversion test successful")
                return True
            else:
                print(f"❌ AAC conversion test failed:")
                print(f"   Error: {test_result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("⚠️  AAC conversion test timed out (might still work)")
            return compatible  # Return the result from codec analysis

        except Exception as e:
            print(f"❌ AAC conversion test error: {e}")
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ ffprobe failed: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse ffprobe output: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def check_project_videos(project_folder):
    """Check all video files in a project folder"""

    project_path = Path(project_folder)

    if not project_path.exists():
        print(f"❌ Project folder does not exist: {project_folder}")
        return

    print(f"🎬 Checking video files in project: {project_folder}")
    print("=" * 60)

    # Check start clip
    start_clip = project_path / "media" / "starting.mp4"
    if start_clip.exists():
        print("\n🎬 Checking START CLIP:")
        check_audio_codec_compatibility(start_clip)
    else:
        print(f"ℹ️  No start clip found at: {start_clip}")

    # Check closing clip
    closing_clip = project_path / "media" / "closing.mov"
    if closing_clip.exists():
        print("\n🏁 Checking CLOSING CLIP:")
        check_audio_codec_compatibility(closing_clip)
    else:
        print(f"ℹ️  No closing clip found at: {closing_clip}")

    # Check media files
    media_folder = project_path / "media"
    if media_folder.exists():
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv'}
        media_files = [f for f in media_folder.iterdir()
                      if f.suffix.lower() in video_extensions
                      and f.name not in ['starting.mp4', 'closing.mov']]

        if media_files:
            print(f"\n📁 Checking {len(media_files)} media file(s):")
            for media_file in media_files:
                print(f"\n📹 Checking {media_file.name}:")
                check_audio_codec_compatibility(media_file)

    print("\n" + "=" * 60)
    print("✅ Audio compatibility check completed")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python audio_compatibility_check.py <project_folder> [specific_file]")
        print("")
        print("Examples:")
        print("  python audio_compatibility_check.py /path/to/project")
        print("  python audio_compatibility_check.py /path/to/project /path/to/specific/video.mp4")
        sys.exit(1)

    if len(sys.argv) == 3:
        # Check specific file
        specific_file = sys.argv[2]
        check_audio_codec_compatibility(specific_file)
    else:
        # Check entire project
        project_folder = sys.argv[1]
        check_project_videos(project_folder)

if __name__ == "__main__":
    main()