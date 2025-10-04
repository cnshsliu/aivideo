import logging
from pathlib import Path
import shutil
import subprocess

from moviepy import AudioFileClip


class BackgroundMusicProcessor:
    """Manages background music addition to videos using FFmpeg"""

    def __init__(self, logger=None, args=None):
        self.logger = logger or logging.getLogger(__name__)
        self.args = args
        self.background_music_info = {}

    def _add_background_music(self, final_clip):
        """Add background music with fade in/out effects to the final video"""
        if not self.args or not getattr(self.args, "mp3", None):
            self.logger.info(
                "No background music file specified, skipping background music"
            )
            return self.background_music_info

        bgm_file = Path(self.args.mp3)
        if not bgm_file.exists():
            self.logger.warning(f"Background music file not found: {bgm_file}")
            return self.background_music_info

        try:
            self.logger.info("🎵 Adding background music...")
            self.logger.info(f"📁 Background music file: {bgm_file}")

            # Get fade parameters
            fade_in_duration = getattr(self.args, "bgm_fade_in", 3.0)
            fade_out_duration = getattr(self.args, "bgm_fade_out", 3.0)
            bgm_volume = getattr(self.args, "bgm_volume", 0.3)

            # Validate parameters
            fade_in_duration = max(0.0, fade_in_duration)
            fade_out_duration = max(0.0, fade_out_duration)
            bgm_volume = max(0.0, min(1.0, bgm_volume))

            self.logger.info(f"⏱️  Fade-in duration: {fade_in_duration}s")
            self.logger.info(f"⏱️  Fade-out duration: {fade_out_duration}s")
            self.logger.info(f"🔊 Volume level: {bgm_volume:.2f}")

            # Due to persistent FFmpeg subprocess issues with MoviePy audio mixing,
            # we'll use a post-processing approach with FFmpeg directly
            # This avoids the 'NoneType' object has no attribute 'stdout' error

            # Store background music info for post-processing
            self.background_music_info = {
                "file": str(bgm_file),
                "fade_in": fade_in_duration,
                "fade_out": fade_out_duration,
                "volume": bgm_volume,
                "video_duration": final_clip.duration if final_clip else 0,
            }

            self.logger.info(
                "🎵 Background music will be added using FFmpeg post-processing"
            )
            self.logger.info("🔄 This avoids MoviePy audio mixing issues")

            return self.background_music_info

        except Exception as e:
            self.logger.error(f"❌ Failed to prepare background music: {e}")
            return self.background_music_info

    def _apply_background_music_ffmpeg(self, input_video):
        """Apply background music to video using FFmpeg directly"""
        if not (hasattr(self, "background_music_info") and self.background_music_info):
            return False
        self.logger.info("🎵 Applying background music using FFmpeg post-processing...")

        # Create temporary file for the video with background music

        temp_video = input_video.with_suffix(".temp_with_music.mp4")
        try:
            # Check if FFmpeg is available
            if not shutil.which("ffmpeg"):
                self.logger.error("❌ FFmpeg not found in PATH")
                return False

            bgm_info = self.background_music_info
            bgm_file = bgm_info["file"]
            video_duration = bgm_info["video_duration"]
            bgm_volume = bgm_info["volume"]
            fade_in = bgm_info["fade_in"]
            fade_out = bgm_info["fade_out"]

            self.logger.info("🎵 Processing background music with FFmpeg...")
            self.logger.info(f"📁 Input video: {input_video}")
            self.logger.info(f"📁 Background music: {bgm_file}")
            self.logger.info(f"⏱️  Video duration: {video_duration:.2f}s")
            self.logger.info(f"🔊 Volume: {bgm_volume:.2f}x")
            self.logger.info(f"🌅 Fade-in: {fade_in}s")
            self.logger.info(f"🌇 Fade-out: {fade_out}s")

            # Build FFmpeg command for audio mixing
            # This approach uses FFmpeg's filter complex to mix audio properly
            ffmpeg_cmd = [
                "ffmpeg",
                "-i",
                str(input_video),  # Input video
                "-i",
                bgm_file,  # Background music
                "-filter_complex",
                self._build_ffmpeg_audio_filter(
                    video_duration, bgm_volume, fade_in, fade_out
                ),
                "-map",
                "0:v",  # Use video from first input
                "-map",
                "[a_out]",  # Use mixed audio
                "-c:v",
                "copy",  # Copy video stream without re-encoding
                "-c:a",
                "aac",  # Audio codec
                "-b:a",
                "192k",  # Audio bitrate
                "-y",  # Overwrite output file
                str(temp_video),
            ]

            self.logger.info(f"🔧 Running FFmpeg command: {' '.join(ffmpeg_cmd)}")

            # Run FFmpeg command
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                self.logger.info(
                    "✅ FFmpeg background music processing completed successfully"
                )
                shutil.move(str(temp_video), str(input_video))
                self.logger.info(
                    "✅ Background music applied successfully using FFmpeg!"
                )
                return True
            else:
                self.logger.error(
                    f"❌ FFmpeg failed with return code: {result.returncode}"
                )
                self.logger.error(f"❌ FFmpeg stderr: {result.stderr}")
                if temp_video.exists():
                    temp_video.unlink()
                return False

        except Exception as e:
            self.logger.error(f"❌ FFmpeg background music processing failed: {e}")
            if temp_video.exists():
                temp_video.unlink()
            return False

    def _build_ffmpeg_audio_filter(self, duration, volume, fade_in, fade_out):
        """Build FFmpeg audio filter complex string for background music"""
        # Build the background music filter with volume
        bgm_filter = f"[1:a]volume={volume}[bgm_vol];"

        # Add fade effects as separate filters - use afade for audio
        fade_filters = ""
        if fade_in > 0 or fade_out > 0:
            fade_filters = "[bgm_vol]"
            if fade_in > 0:
                fade_filters += f"afade=t=in:st=0:d={fade_in}"
            if fade_out > 0:
                fade_out_start = max(0, duration - fade_out)
                if fade_in > 0:
                    fade_filters += f",afade=t=out:st={fade_out_start}:d={fade_out}"
                else:
                    fade_filters += f"afade=t=out:st={fade_out_start}:d={fade_out}"
            fade_filters += "[bgm];"
        else:
            fade_filters = "[bgm_vol][bgm];"

        # Mix the background music with original audio
        # If the video has audio, mix them; otherwise, just use background music
        mix_filter = (
            "[0:a][bgm]amix=inputs=2:duration=shortest:dropout_transition=2[a_out]"
        )

        return bgm_filter + fade_filters + mix_filter
