import os
import sys
import random
import time
import subprocess
import shutil
from pathlib import Path
from typing import TypeVar
import json
from datetime import datetime
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

# Removed audio effects imports to avoid subprocess issues
import websockets
import uuid
import struct
import io
import asyncio

# Import configuration module
from subtitle_processor import SubtitleProcessor
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
        self.subtitle_processor = SubtitleProcessor(self.logger)

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

    def _log_subtitles(self, source="unknown"):
        """Log generated subtitles with detailed information"""
        if not self.subtitles:
            self.logger.warning("No subtitles to log")
            return

        self.logger.info(f"=== GENERATED SUBTILES ({source}) ===")
        self.logger.info(f"Total subtitles: {len(self.subtitles)}")

        for i, subtitle in enumerate(self.subtitles, 1):
            self.logger.info(
                f"Subtitle {i}: '{subtitle}' (length: {len(subtitle)} chars)"
            )

        self.logger.info("=== END SUBTILES ===")

        # Also save subtitles to a dedicated file
        subtitle_file = (
            self.project_folder
            / "logs"
            / f"subtitles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        with open(subtitle_file, "w", encoding="utf-8") as f:
            f.write(f"Generated Subtitles ({source})\n")
            f.write(f"Project: {self.project_folder}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total: {len(self.subtitles)} subtitles\n")
            f.write("=" * 50 + "\n\n")

            for i, subtitle in enumerate(self.subtitles, 1):
                f.write(f"{i}. {subtitle}\n")

        self.logger.info(f"Subtitles saved to: {subtitle_file}")

    # Subtitle processing wrapper methods
    def _optimize_subtitles(self, raw_subtitles):
        """Optimize subtitles for display while preserving timing relationships."""
        # Set up subtitle processor with current state
        self.subtitle_processor.voice_subtitles = self.voice_subtitles
        self.subtitle_processor.display_subtitles = self.display_subtitles
        self.subtitle_processor.display_to_voice_mapping = self.display_to_voice_mapping

        # Call subtitle processor
        result = self.subtitle_processor._optimize_subtitles(raw_subtitles)

        # Update state from subtitle processor
        self.voice_subtitles = self.subtitle_processor.voice_subtitles
        self.display_subtitles = self.subtitle_processor.display_subtitles
        self.display_to_voice_mapping = self.subtitle_processor.display_to_voice_mapping

        return result

    def _calculate_subtitle_timestamps(self):
        """Calculate intelligent timestamps for display subtitles based on voice subtitles and audio duration"""
        # Set up subtitle processor with current state
        self.subtitle_processor.subtitle_folder = self.subtitle_folder
        self.subtitle_processor.audio_file = self.audio_file
        self.subtitle_processor.voice_subtitles = self.voice_subtitles
        self.subtitle_processor.display_subtitles = self.display_subtitles
        self.subtitle_processor.display_to_voice_mapping = self.display_to_voice_mapping

        # Call subtitle processor
        self.subtitle_processor._calculate_subtitle_timestamps()

        # Update state from subtitle processor
        self.subtitle_timestamps = self.subtitle_processor.subtitle_timestamps

    def _create_fallback_timestamps(self):
        """Create fallback timestamps with equal distribution based on display subtitles"""
        # Set up subtitle processor with current state
        self.subtitle_processor.subtitle_folder = self.subtitle_folder
        self.subtitle_processor.audio_file = self.audio_file
        self.subtitle_processor.display_subtitles = self.display_subtitles

        # Call subtitle processor
        self.subtitle_processor._create_fallback_timestamps()

        # Update state from subtitle processor
        self.subtitle_timestamps = self.subtitle_processor.subtitle_timestamps

    def _create_srt_subtitle_file(self):
        """Create SRT subtitle file from timestamps"""
        # Set up subtitle processor with current state
        self.subtitle_processor.subtitle_folder = self.subtitle_folder
        self.subtitle_processor.subtitle_timestamps = self.subtitle_timestamps

        # Call subtitle processor
        self.subtitle_processor._create_srt_subtitle_file()

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

    def load_existing_subtitles(self):
        """Load existing subtitles from voice_subtitles.txt and display_subtitles.txt, or fallback to generated_subtitles.txt"""
        # First try to load the dual text system files
        voice_file = self.subtitle_folder / "voice_subtitles.txt"
        display_file = self.subtitle_folder / "display_subtitles.txt"

        if voice_file.exists() and display_file.exists():
            try:
                # Load voice subtitles
                with open(voice_file, "r", encoding="utf-8") as f:
                    voice_content = f.read().strip()
                    if voice_content:
                        self.voice_subtitles = [
                            line.strip()
                            for line in voice_content.split("\n")
                            if line.strip()
                        ]

                # Load display subtitles
                with open(display_file, "r", encoding="utf-8") as f:
                    display_content = f.read().strip()
                    if display_content:
                        self.display_subtitles = [
                            line.strip()
                            for line in display_content.split("\n")
                            if line.strip()
                        ]

                if self.voice_subtitles and self.display_subtitles:
                    self.subtitles = (
                        self.display_subtitles
                    )  # Use display for main workflow
                    # Create display-to-voice mapping for timestamp calculation
                    self.display_to_voice_mapping = (
                        self.subtitle_processor._create_display_voice_mapping(
                            self.voice_subtitles, self.display_subtitles
                        )
                    )
                    print(
                        f"Loaded {len(self.voice_subtitles)} voice subtitles and {len(self.display_subtitles)} display subtitles"
                    )
                    return True
            except Exception as e:
                print(f"Error loading dual text subtitles: {e}")

        # Fallback to old generated_subtitles.txt
        subtitles_file = self.subtitle_folder / "generated_subtitles.txt"
        if subtitles_file.exists():
            try:
                with open(subtitles_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        raw_subtitles = [
                            line.strip() for line in content.split("\n") if line.strip()
                        ]
                        if raw_subtitles:
                            # Create both voice and display versions
                            self.voice_subtitles = raw_subtitles
                            # Create display-optimized subtitles (without unnecessary punctuation)
                            self.display_subtitles = self._optimize_subtitles(
                                raw_subtitles
                            )
                            self.subtitles = self.display_subtitles

                            # Save both versions for future use
                            with open(voice_file, "w", encoding="utf-8") as f:
                                f.write("\n".join(self.voice_subtitles))
                            with open(display_file, "w", encoding="utf-8") as f:
                                f.write("\n".join(self.display_subtitles))

                            print(
                                f"Loaded {len(self.voice_subtitles)} voice subtitles and created {len(self.display_subtitles)} display subtitles"
                            )
                            return True
            except Exception as e:
                print(f"Error loading existing subtitles: {e}")
        return False

    def load_text_file_subtitles(self, text_file_path):
        """Load subtitles from specified text file and create voice/display versions"""
        text_file = Path(text_file_path)
        if not text_file.exists():
            raise FileNotFoundError(f"Text file not found: {text_file}")

        try:
            with open(text_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    # Load original subtitles as voice subtitles (with punctuation)
                    self.voice_subtitles = [
                        line.strip() for line in content.split("\n") if line.strip()
                    ]

                    # Create display-optimized subtitles (without unnecessary punctuation)
                    self.display_subtitles = self._optimize_subtitles(
                        self.voice_subtitles
                    )

                    # Use display subtitles for main workflow
                    self.subtitles = self.display_subtitles

                    if self.voice_subtitles:
                        print(
                            f"Loaded {len(self.voice_subtitles)} voice subtitles and created {len(self.display_subtitles)} display subtitles from {text_file}"
                        )
                        self._log_subtitles(f"text file: {text_file.name}")

                        # Save both versions
                        voice_file = self.subtitle_folder / "voice_subtitles.txt"
                        display_file = self.subtitle_folder / "display_subtitles.txt"

                        with open(voice_file, "w", encoding="utf-8") as f:
                            f.write("\n".join(self.voice_subtitles))

                        with open(display_file, "w", encoding="utf-8") as f:
                            f.write("\n".join(self.display_subtitles))

                        return True
        except Exception as e:
            print(f"Damn, failed to read text file {text_file}: {e}")

        return False

    def load_static_subtitles(self):
        """Load static subtitles from .txt files (excluding generated_subtitles.txt)"""
        txt_files = list(self.subtitle_folder.glob("*.txt"))
        # Skip generated_subtitles.txt and also skip voice/display files if they exist
        txt_files = [
            f
            for f in txt_files
            if f.name
            not in [
                "generated_subtitles.txt",
                "voice_subtitles.txt",
                "display_subtitles.txt",
            ]
        ]

        if not txt_files:
            return False

        # Read all .txt files and combine their content
        raw_subtitles = []
        for txt_file in sorted(txt_files):
            try:
                with open(txt_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        # Split content by newlines for multiple subtitles
                        lines = [
                            line.strip() for line in content.split("\n") if line.strip()
                        ]
                        raw_subtitles.extend(lines)
                        print(f"Loaded {len(lines)} subtitles from {txt_file.name}")
            except Exception as e:
                print(f"Damn, failed to read {txt_file}: {e}")
                continue

        if not raw_subtitles:
            return False

        # Store original subtitles for voice generation (with punctuation)
        self.voice_subtitles = raw_subtitles

        # Create display-optimized subtitles (without unnecessary punctuation)
        self.display_subtitles = self._optimize_subtitles(raw_subtitles)

        # Use display subtitles for the main workflow (backward compatibility)
        self.subtitles = self.display_subtitles

        print(
            f"Loaded {len(self.voice_subtitles)} voice subtitles and created {len(self.display_subtitles)} display subtitles from static files"
        )
        self._log_subtitles("static files")

        # Save both versions
        voice_file = self.subtitle_folder / "voice_subtitles.txt"
        display_file = self.subtitle_folder / "display_subtitles.txt"

        with open(voice_file, "w", encoding="utf-8") as f:
            f.write("\n".join(self.voice_subtitles))

        with open(display_file, "w", encoding="utf-8") as f:
            f.write("\n".join(self.display_subtitles))

        return True

    def get_llm_model_config(self, provider):
        """Get model configuration for specified LLM provider"""
        return self.config.get_llm_model_config(provider)

    def generate_subtitles(self):
        """Generate subtitles using LLM"""
        self.logger.info("Generating subtitles using LLM...")

        # Read prompt file
        prompt_file = self.prompt_folder / "prompt.md"
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        # Generate subtitles using LLMManager
        self.voice_subtitles, self.display_subtitles = (
            self.llm_manager.generate_subtitles(
                self.args, self.prompt_folder, self.subtitle_folder, self.logger
            )
        )

        # Optimize display subtitles
        self.display_subtitles = self._optimize_subtitles(self.voice_subtitles)

        # Use display subtitles for the main workflow (backward compatibility)
        self.subtitles = self.display_subtitles
        self._log_subtitles("LLM - Generated")

        return True

    def generate_audio(self):
        """Generate audio from subtitles using Volcengine TTS"""
        # Use voice_subtitles (with punctuation) for audio generation
        if not hasattr(self, "voice_subtitles") or not self.voice_subtitles:
            raise ValueError("No voice subtitles available for audio generation")

        # Get Volcengine credentials from environment variables
        app_id = os.getenv("VOLCENGINE_APP_ID")
        access_token = os.getenv("VOLCENGINE_ACCESS_TOKEN")

        if not app_id:
            raise ValueError("VOLCENGINE_APP_ID not found in environment variables")
        if not access_token:
            raise ValueError(
                "VOLCENGINE_ACCESS_TOKEN not found in environment variables"
            )

        # Combine all voice subtitles for full audio (with punctuation for natural speech)
        full_text = " ".join(self.voice_subtitles)

        try:
            # Generate audio using Volcengine TTS
            audio_path = self.project_folder / "generated_audio.mp3"

            # Run the async Volcengine TTS function
            audio_data = asyncio.run(
                self._generate_audio_volcengine(app_id, access_token, full_text)
            )

            if audio_data:
                with open(audio_path, "wb") as f:
                    f.write(audio_data)
                print(f"Audio file saved to: {audio_path}")
            else:
                raise Exception("No audio data received from Volcengine TTS")

            self.audio_file = audio_path

            # Calculate subtitle timestamps based on audio duration and subtitle count
            self._calculate_subtitle_timestamps()

        except Exception as e:
            print(f"Damn, Volcengine TTS failed: {e}")
            print("Voice generation failed - exiting program")
            sys.exit(1)

    async def _generate_audio_volcengine(
        self, app_id: str, access_token: str, text: str
    ) -> bytes:
        """Generate audio using Volcengine TTS WebSocket API"""
        endpoint = "wss://openspeech.bytedance.com/api/v1/tts/ws_binary"

        # Prepare request payload
        request = {
            "app": {
                "appid": app_id,
                "token": access_token,
                "cluster": "volcano_tts",
            },
            "user": {
                "uid": str(uuid.uuid4()),
            },
            "audio": {
                "voice_type": "zh_female_shuangkuaisisi_moon_bigtts",
                "encoding": "mp3",
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "operation": "submit",
                "with_timestamp": "1",
                "extra_param": json.dumps(
                    {
                        "disable_markdown_filter": False,
                    }
                ),
            },
        }

        headers = {
            "Authorization": f"Bearer;{access_token}",
        }

        audio_data = bytearray()

        try:
            # Initialize WebSocket message counter for dot display
            self._websocket_message_count = 0
            self._last_dot_print_time = 0

            # Connect to Volcengine WebSocket
            async with websockets.connect(
                endpoint, additional_headers=headers, max_size=10 * 1024 * 1024
            ) as websocket:
                print("Connected to Volcengine TTS WebSocket")

                # Send the TTS request
                await self._volcengine_full_client_request(
                    websocket, json.dumps(request).encode()
                )

                print("Receiving audio data", end="", flush=True)

                # Receive audio data
                while True:
                    msg = await self._volcengine_receive_message(websocket)

                    if msg.type == self._volcengine_msg_type("FrontEndResultServer"):
                        continue
                    elif msg.type == self._volcengine_msg_type("AudioOnlyServer"):
                        audio_data.extend(msg.payload)
                        if msg.sequence < 0:  # Last message
                            break
                    else:
                        raise RuntimeError(f"TTS conversion failed: {msg}")

                # Print newline after dots are done
                print()  # Newline after the dots
                return bytes(audio_data)

        except Exception as e:
            print(f"Volcengine TTS WebSocket error: {e}")
            raise

    def _volcengine_msg_type(self, name: str):
        """Get Volcengine message type by name"""

        class MsgType:
            Invalid = 0
            FullClientRequest = 0b1
            AudioOnlyClient = 0b10
            FullServerResponse = 0b1001
            AudioOnlyServer = 0b1011
            FrontEndResultServer = 0b1100
            Error = 0b1111

        return getattr(MsgType, name, MsgType.Invalid)

    class VolcengineMessage:
        """Simplified Volcengine message class"""

        def __init__(self, type_value=0, flag=0, sequence=0, payload=b""):
            self.type = type_value
            self.flag = flag
            self.sequence = sequence
            self.payload = payload

        def marshal(self):
            """Serialize message to bytes"""
            buffer = io.BytesIO()

            # Write header
            version = 1
            header_size = 1  # HeaderSize4 = 1 means 4*1=4 bytes
            serialization = 1  # JSON = 1
            compression = 0  # None = 0

            header = [
                (version << 4) | header_size,
                (self.type << 4) | self.flag,
                (serialization << 4) | compression,
            ]

            # Add padding to make header exactly 4 bytes
            header_size_bytes = 4 * header_size
            if padding := header_size_bytes - len(header):
                header.extend([0] * padding)

            buffer.write(bytes(header))

            # Write sequence number if needed
            if self.flag in [1, 3]:  # PositiveSeq or NegativeSeq
                buffer.write(struct.pack(">i", self.sequence))

            # Write payload with size
            size = len(self.payload)
            buffer.write(struct.pack(">I", size))
            buffer.write(self.payload)

            return buffer.getvalue()

        @classmethod
        def from_bytes(cls, data: bytes):
            """Create message from bytes"""
            if len(data) < 3:
                raise ValueError(
                    f"Data too short: expected at least 3 bytes, got {len(data)}"
                )

            type_and_flag = data[1]
            msg_type = type_and_flag >> 4
            flag = type_and_flag & 0b00001111

            msg = cls(type_value=msg_type, flag=flag)
            msg.unmarshal(data)
            return msg

        def unmarshal(self, data: bytes):
            """Parse message data"""
            buffer = io.BytesIO(data)

            # Read version and header size
            version_and_header_size = buffer.read(1)[0]
            header_size = version_and_header_size & 0b00001111

            # Skip second byte
            buffer.read(1)

            # Read serialization and compression methods
            buffer.read(1)

            # Skip header padding
            read_size = 3
            if padding_size := header_size * 4 - read_size:
                buffer.read(padding_size)

            # Read sequence number if needed
            if self.flag in [1, 3]:  # PositiveSeq or NegativeSeq
                sequence_bytes = buffer.read(4)
                if sequence_bytes:
                    self.sequence = struct.unpack(">i", sequence_bytes)[0]

            # Read payload
            size_bytes = buffer.read(4)
            if size_bytes:
                size = struct.unpack(">I", size_bytes)[0]
                if size > 0:
                    self.payload = buffer.read(size)

            # Check for remaining data
            remaining = buffer.read()
            if remaining:
                raise ValueError(f"Unexpected data after message: {remaining}")

        def __str__(self):
            return f"Type: {self.type}, Flag: {self.flag}, Sequence: {self.sequence}, PayloadSize: {len(self.payload)}"

    async def _volcengine_receive_message(self, websocket):
        """Receive message from Volcengine WebSocket"""
        try:
            data = await websocket.recv()
            if isinstance(data, str):
                raise ValueError(f"Unexpected text message: {data}")
            elif isinstance(data, bytes):
                msg = self.VolcengineMessage.from_bytes(data)

                # Show continuous dots instead of detailed log messages
                if not hasattr(self, "_websocket_message_count"):
                    self._websocket_message_count = 0
                    self._last_dot_print_time = 0

                self._websocket_message_count += 1

                # Print dots progressively (every 10 messages)
                import time

                current_time = time.time()
                if (
                    self._websocket_message_count % 10 == 0
                    or current_time - self._last_dot_print_time > 1.0
                ):
                    print(".", end="", flush=True)
                    self._last_dot_print_time = current_time

                return msg
            else:
                raise ValueError(f"Unexpected message type: {type(data)}")
        except Exception as e:
            print(f"Failed to receive message: {e}")
            raise

    async def _volcengine_full_client_request(self, websocket, payload: bytes):
        """Send full client request to Volcengine"""
        msg = self.VolcengineMessage(type_value=0b1, flag=0)  # FullClientRequest, NoSeq
        msg.payload = payload

        data = msg.marshal()
        print(f"Sending: {msg}")
        print(f"Raw data length: {len(data)}")
        print(f"Raw data (hex): {data.hex()}")
        await websocket.send(data)

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
                print("HERE1")
                scaled_clip = clip.with_effects(
                    [vfx.Resize(new_size=(scaled_width, scaled_height))]
                )
                print("HERE2")

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

    def _add_title_basic(self, clip, use_full_duration=False):
        """Add title to clip with Chinese font support

        Args:
            clip: The video clip to add title to
            use_full_duration: If True, use full clip duration regardless of title_length setting
        """
        if not self.args.title:
            return clip

        try:
            # Determine title duration
            if use_full_duration:
                title_duration = clip.duration
            else:
                title_duration = getattr(self.args, "title_length", 3.0)
                if title_duration is None:
                    title_duration = 3.0
                if title_duration > clip.duration:
                    title_duration = clip.duration

            self.logger.info(
                f"Adding title with duration: {title_duration}s to clip of duration: {clip.duration}s"
            )

            # Parse title - split by comma for multi-line
            title_lines = self.args.title.split(",")
            font_size = getattr(self.args, "title_font_size", 60)
            if font_size is None:
                font_size = 60
            title_font = (
                getattr(self.args, "title_font", "Arial-Black") or "Arial-Black"
            )

            # Check if title contains Chinese and use appropriate font
            full_title_text = self.args.title
            if clip and contains_chinese(full_title_text):
                self.logger.info(f"Chinese text detected in title: '{full_title_text}'")
                title_font = get_chinese_compatible_font(title_font)
                if title_font is None:
                    self.logger.error("No compatible font found for Chinese title text")
                    return clip

            title_clips = []
            title_position = getattr(self.args, "title_position", 20)
            if title_position is None:
                title_position = 20
            y_offset = title_position / 100 * clip.h

            for i, line in enumerate(title_lines):
                # Adjust font size for subsequent lines
                current_font_size = font_size if i == 0 else int(font_size * 0.9)

                try:
                    # Test if the font is valid by trying to create a small text clip first
                    test_clip = TextClip(
                        title_font,
                        "Test",
                        font_size=12,
                        color="white",
                        stroke_color="black",
                        stroke_width=1,
                        method="label",
                    )
                    test_clip.close()

                    # Create the actual title clip
                    title_clip = TextClip(
                        title_font,
                        line.strip(),
                        font_size=current_font_size,
                        color="yellow",
                        stroke_color="black",
                        stroke_width=4,
                        method="label",
                    )

                    # Verify the clip was created successfully
                    if title_clip is None:
                        raise ValueError("TextClip returned None")

                    # Position the title
                    if clip and title_clip:
                        title_x = clip.w / 2 - title_clip.w / 2
                        title_y = y_offset + i * (current_font_size + 10)

                        title_clip = title_clip.with_position((title_x, title_y))
                        # Show title only for the specified duration
                        title_clip = title_clip.with_duration(title_duration)
                    if title_clip:
                        title_clips.append(title_clip)
                except Exception as text_error:
                    print(
                        f"Damn, title text clip creation failed for line '{line.strip()}': {text_error}"
                    )
                    # Try fallback font
                    try:
                        fallback_font = "Arial-Bold"
                        self.logger.info(f"Trying fallback font: {fallback_font}")
                        title_clip = TextClip(
                            fallback_font,
                            line.strip(),
                            font_size=current_font_size,
                            color="yellow",
                            stroke_color="black",
                            stroke_width=4,
                            method="label",
                        )

                        if title_clip is None:
                            raise ValueError("Fallback TextClip returned None")

                        # Position the title
                        if clip and title_clip:
                            title_x = clip.w / 2 - title_clip.w / 2
                            title_y = y_offset + i * (current_font_size + 10)

                            title_clip = title_clip.with_position((title_x, title_y))
                            title_clip = title_clip.with_duration(title_duration)
                            title_clips.append(title_clip)
                        self.logger.info(
                            "Successfully created title with fallback font"
                        )
                    except Exception as fallback_error:
                        print(f"Damn, fallback font also failed: {fallback_error}")
                        continue

            if not title_clips:
                print("No title clips created, returning original clip")
                return clip

            # Filter out any None clips that might have been created
            title_clips = [clip for clip in title_clips if clip is not None]
            if not title_clips:
                print("All title clips were None, returning original clip")
                return clip

            # If title duration is less than clip duration, we need to split the clip
            if title_duration < clip.duration:
                try:
                    # Verify the clip is valid before subclip operations
                    if clip is None:
                        raise ValueError("Original clip is None")

                    # Test if the clip can be read
                    try:
                        test_frame = clip.get_frame(0.0)
                        if test_frame is None or not isinstance(test_frame, np.ndarray):
                            raise ValueError("Cannot get frame from original clip")
                    except Exception as frame_error:
                        raise ValueError(
                            f"Cannot read frames from original clip: {frame_error}"
                        )

                    # Create a version with title for the title duration
                    clip_with_title = clip.subclipped(0, title_duration)
                    if clip_with_title is None:
                        raise ValueError("clip_with_title is None after subclip")

                    # Test the subclipped clip
                    try:
                        test_frame = clip_with_title.get_frame(0.0)
                        if test_frame is None or not isinstance(test_frame, np.ndarray):
                            raise ValueError("Cannot get frame from clip_with_title")
                    except Exception as frame_error:
                        raise ValueError(
                            f"Cannot read frames from clip_with_title: {frame_error}"
                        )

                    # Create composite with all title clips
                    all_clips = [clip_with_title] + title_clips
                    # Filter out any None clips
                    all_clips = [c for c in all_clips if c is not None]

                    # Verify all clips before creating composite
                    for i, test_clip in enumerate(all_clips):
                        if test_clip is None:
                            raise ValueError(f"Clip {i} is None")
                        try:
                            test_frame = test_clip.get_frame(0.0)
                            if test_frame is None or not isinstance(
                                test_frame, np.ndarray
                            ):
                                raise ValueError(f"Cannot get frame from clip {i}")
                        except Exception as frame_error:
                            raise ValueError(
                                f"Cannot read frames from clip {i}: {frame_error}"
                            )

                    titled_clip = CompositeVideoClip(all_clips)
                    titled_clip = titled_clip.with_duration(title_duration)

                    # Create the remaining part of the clip without title
                    remaining_clip = clip.subclipped(title_duration)
                    if remaining_clip is None:
                        raise ValueError("remaining_clip is None after subclip")

                    # Test the remaining clip
                    try:
                        test_frame = remaining_clip.get_frame(0.0)
                        if test_frame is None or not isinstance(test_frame, np.ndarray):
                            raise ValueError("Cannot get frame from remaining_clip")
                    except Exception as frame_error:
                        raise ValueError(
                            f"Cannot read frames from remaining_clip: {frame_error}"
                        )

                    # Ensure the remaining clip maintains the original video content
                    # Create a composite clip for the remaining part to avoid black screen
                    remaining_composite = None
                    if remaining_clip:
                        remaining_composite = CompositeVideoClip([remaining_clip])
                        remaining_composite = remaining_composite.with_duration(
                            remaining_clip.duration
                        )

                    # Return both clips concatenated
                    clips_to_concat = [titled_clip]
                    if remaining_composite:
                        clips_to_concat.append(remaining_composite)

                    result = self._safe_concatenate_clips(
                        clips_to_concat, method="compose"
                    )
                    remaining_duration = (
                        remaining_composite.duration if remaining_composite else 0
                    )
                    titled_duration = titled_clip.duration if titled_clip else 0
                    result_duration = result.duration if result else 0
                    self.logger.info(
                        f"Created titled clip: {titled_duration}s + remaining clip: {remaining_duration}s = {result_duration}s"
                    )
                    return result
                except Exception as subclip_error:
                    self.logger.error(f"Error during clip splitting: {subclip_error}")
                    # Fallback: return original clip without title
                    return clip
            else:
                # Title covers the entire clip
                try:
                    all_clips = [clip] + title_clips
                    # Filter out any None clips
                    all_clips = [c for c in all_clips if c is not None]

                    result = CompositeVideoClip(all_clips)
                    if clip:
                        result = result.with_duration(clip.duration)
                    if result:
                        self.logger.info(
                            f"Title covers entire clip: {result.duration}s"
                        )
                    return result
                except Exception as composite_error:
                    self.logger.error(
                        f"Error during composite creation: {composite_error}"
                    )
                    # Fallback: return original clip without title
                    return clip

        except Exception as e:
            print(f"Damn, title creation failed: {e}")
            self.logger.error(f"Title creation failed: {e}")
            return clip

    def add_title(self, clip, use_full_duration=False):
        """Add prominent title to clip with enhanced visibility"""
        if not self.args.title:
            return clip

        try:
            # TEMPORARY: Disable enhanced title system due to frame read issues
            self.logger.info(
                "Enhanced titles disabled temporarily due to frame read issues, using basic title system"
            )
            return self._add_title_basic(clip, use_full_duration)

            # Original enhanced title system (disabled for now)
            # if ENHANCED_TITLES_AVAILABLE:
            #     self.logger.info(f"Using enhanced title system for: '{self.args.title}'")
            #     return add_prominent_title_to_clip(clip, self.args.title, self.args)
            #
            # # Fallback to original method
            # self.logger.info("Enhanced titles not available, using basic title system")
            # return self._add_title_basic(clip, use_full_duration)

        except Exception as e:
            self.logger.error(f"Enhanced title failed, falling back to basic: {e}")
            # Fallback to basic title
            return self._add_title_basic(clip, use_full_duration)

    def add_subtitles(self, clip, subtitle_text):
        """Legacy method: Add single subtitle to clip with Chinese font support"""
        if not subtitle_text:
            return clip

        try:
            font_size = getattr(self.args, "subtitle_font_size", 48)
            if font_size is None:
                font_size = 48
            subtitle_font = getattr(self.args, "subtitle_font", "Arial") or "Arial"

            # Check if text contains Chinese and use appropriate font
            if contains_chinese(subtitle_text):
                self.logger.info(f"Chinese text detected: '{subtitle_text}'")
                subtitle_font = get_chinese_compatible_font(subtitle_font)
                if subtitle_font is None:
                    self.logger.error("No compatible font found for Chinese text")
                    return clip

            self.logger.info(f"Creating subtitle with font: {subtitle_font}")

            # Calculate maximum text width for mobile portrait video with proper margins
            # For 1080px width: 15% margins = 162px each side, text area = 756px
            max_text_width = int(clip.w * 0.65)  # Reduced to 65% for mobile safety

            subtitle_clip = TextClip(
                subtitle_font,
                subtitle_text,
                font_size=font_size,
                color="white",
                stroke_color="black",
                stroke_width=1,
                size=(max_text_width, None),  # Strict width limit
                method="caption",  # Enable text wrapping
                text_align="center",  # Center alignment
                transparent=True,
            )

            # Position subtitle (centered)
            subtitle_position = getattr(self.args, "subtitle_position", 80)
            if subtitle_position is None:
                subtitle_position = 80
            y_position = subtitle_position / 100 * clip.h
            subtitle_x = clip.w / 2 - subtitle_clip.w / 2
            subtitle_y = y_position

            # Safety check: if text is still too wide, enforce strict limits
            if subtitle_clip.w > max_text_width:
                self.logger.warning(
                    f"Text still too wide after wrapping: {subtitle_clip.w} > {max_text_width}"
                )
                subtitle_clip.close()
                # Try with much smaller font size - more aggressive reduction for mobile
                if contains_chinese(subtitle_text):
                    emergency_font_size = max(
                        16, int(font_size * 0.4)
                    )  # 40% reduction for Chinese
                else:
                    emergency_font_size = max(
                        18, int(font_size * 0.5)
                    )  # 50% reduction for English
                self.logger.info(
                    f"Emergency font size reduction: {font_size} → {emergency_font_size}"
                )
                subtitle_clip = TextClip(
                    subtitle_font,
                    subtitle_text,
                    font_size=emergency_font_size,
                    color="white",
                    stroke_color="black",
                    stroke_width=1,
                    size=(max_text_width, None),
                    method="caption",
                    text_align="center",
                    transparent=True,
                )
                subtitle_x = clip.w / 2 - subtitle_clip.w / 2  # type: ignore

                # Final safety check - if still too wide, force width scaling
                if subtitle_clip.w > max_text_width:  # type: ignore
                    self.logger.error(
                        f"Text still exceeds width after emergency reduction: {subtitle_clip.w} > {max_text_width}"  # type: ignore
                    )
                    # Force scale the text clip width to fit exactly
                    force_scale = max_text_width / subtitle_clip.w  # type: ignore
                    subtitle_clip = subtitle_clip.with_effects(
                        [vfx.Resize(new_size=force_scale)]
                    )
                    subtitle_x = clip.w / 2 - subtitle_clip.w / 2  # type: ignore
                    self.logger.info(f"Applied forced scaling: {force_scale:.2f}x")
                    self.logger.error(
                        "WARNING: Text was scaled down to fit - consider shortening subtitle text"
                    )
                else:
                    self.logger.info(
                        f"Reduced font size to {emergency_font_size} to fit text"
                    )

            subtitle_clip = subtitle_clip.with_position((subtitle_x, subtitle_y))  # type: ignore

            result = CompositeVideoClip([clip, subtitle_clip])
            # Ensure the composite clip has the same duration as the original
            result = result.with_duration(clip.duration)  # type: ignore
            return result

        except Exception as e:
            self.logger.error(f"Subtitle creation failed for '{subtitle_text}': {e}")
            print(f"Damn, subtitle creation failed for '{subtitle_text}': {e}")
            return clip

    def add_timestamped_subtitles(self, video_clip):
        """Add all subtitles with their specific timestamps to the video"""
        if not hasattr(self, "subtitle_timestamps") or not self.subtitle_timestamps:
            self.logger.warning(
                "No timestamped subtitles available, using fallback method"
            )
            # Fallback to old method if timestamps not available
            return self._add_subtitles_fallback(video_clip)

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

    def _add_subtitles_fallback(self, video_clip):
        """Fallback method: distribute subtitles evenly across video clips"""
        if not self.subtitles:
            return video_clip

        try:
            self.logger.info("Using fallback subtitle distribution method")

            # If we have processed clips, add subtitles to each clip
            # This requires modifying the clip processing logic
            return video_clip

        except Exception as e:
            self.logger.error(f"Fallback subtitle method failed: {e}")
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

    def _add_background_music(self, final_clip):
        """Add background music with fade in/out effects to the final video"""
        if not getattr(self.args, "mp3", None):
            self.logger.info(
                "No background music file specified, skipping background music"
            )
            return final_clip

        bgm_file = Path(self.args.mp3)
        if not bgm_file.exists():
            self.logger.warning(f"Background music file not found: {bgm_file}")
            return final_clip

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

            return final_clip

        except Exception as e:
            self.logger.error(f"❌ Failed to prepare background music: {e}")
            self.logger.error(f"Error type: {type(e)}")
            import traceback

            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.logger.info("🔄 Continuing without background music...")
            return final_clip

    def _apply_background_music_ffmpeg(self, input_video, output_video):
        """Apply background music to video using FFmpeg directly"""
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
                str(output_video),
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
                return True
            else:
                self.logger.error(
                    f"❌ FFmpeg failed with return code: {result.returncode}"
                )
                self.logger.error(f"❌ FFmpeg stderr: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"❌ FFmpeg background music processing failed: {e}")
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

    def _regenerate_with_mobile_portrait_ratio(
        self, video_file, current_width, current_height
    ):
        """Regenerate video by cropping from center to 9:16 (width:height) aspect ratio"""
        import subprocess

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

    def _regenerate_with_16_9_aspect_ratio(
        self, video_file, current_width, current_height
    ):
        """Regenerate video with 16:9 aspect ratio using ffmpeg"""
        import subprocess

        try:
            # Create temporary file for the corrected video
            temp_file = video_file.with_suffix(".temp.mp4")

            # Calculate target dimensions for standard 16:9 (width:height)
            # Choose the closest standard 16:9 resolution
            standard_sizes = [
                (3840, 2160),  # 4K
                (2560, 1440),  # 2K
                (1920, 1080),  # Full HD
                (1600, 900),  # HD+
                (1366, 768),  # Common laptop
                (1280, 720),  # HD
            ]

            # Find the closest standard size based on current width
            best_size = (1920, 1080)  # Default to Full HD
            min_diff = float("inf")

            for std_width, std_height in standard_sizes:
                diff = abs(current_width - std_width)
                if diff < min_diff:
                    min_diff = diff
                    best_size = (std_width, std_height)

            target_width, target_height = best_size

            self.logger.info(
                f"Selected standard 16:9 size: {target_width}x{target_height} (closest to {current_width}x{current_height})"
            )
            self.logger.info(
                f"Resizing from {current_width}x{current_height} to {target_width}x{target_height}"
            )

            # Use ffmpeg to resize the video
            cmd = [
                "ffmpeg",
                "-i",
                str(video_file),
                "-vf",
                f"scale={target_width}:{target_height}",
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

            print("🎬 Regenerating video with ffmpeg...")
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
                    f"Video regenerated successfully: {target_width}x{target_height}"
                )
                print(
                    f"✅ Video regenerated successfully: {target_width}x{target_height}"
                )
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
            self.logger.error(f"Error regenerating video: {e}")
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
            if self.load_text_file_subtitles(self.args.text):
                # Text file loaded successfully, now decide about voice generation
                if self.args.gen_voice:
                    self.logger.info("Generating voice for text file subtitles...")
                    self.generate_audio()
                else:
                    # Check if existing audio file exists
                    audio_file = self.project_folder / "generated_audio.mp3"
                    if audio_file.exists():
                        self.audio_file = audio_file
                        self.logger.info("Using existing audio file")
                        # Calculate subtitle timestamps using existing audio
                        self._calculate_subtitle_timestamps()
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
                if self.load_existing_subtitles():
                    self.logger.info("Using existing generated subtitles")
                else:
                    # If no existing generated subtitles, try static files
                    if self.load_static_subtitles():
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
                self._log_subtitles("LLM - Generated")

            # Generate audio if needed
            if voice_needs_generation:
                self.logger.info("Generating new audio...")
                self.generate_audio()
            else:
                # Check if existing audio file exists
                audio_file = self.project_folder / "generated_audio.mp3"
                if audio_file.exists():
                    self.audio_file = audio_file
                    self.logger.info("Using existing audio file")
                    # Calculate subtitle timestamps using existing audio (for both existing and new subtitles)
                    if hasattr(self, "voice_subtitles") and self.voice_subtitles:
                        self._calculate_subtitle_timestamps()
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
                    clip = self.add_title(clip, use_full_duration=True)
                elif i == 0:
                    clip = self.add_title(clip)

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
                    start_clip = self.add_title(start_clip, use_full_duration=True)
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
            final_clip = self._add_background_music(final_clip)
            self.logger.info(
                f"Final video duration after adding background music: {final_clip.duration:.2f}s"
            )

        # Write output file
        output_file = self.project_folder / "output.mp4"
        self.logger.info(f"Writing video to: {output_file}")
        print(f"Writing video to: {output_file}")

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

            print("Video writing in progress...")

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
        print("Starting video rendering... This may take a while.")
        self.logger.info("Starting video rendering process")

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

        print("Video writing completed!")

        # Apply background music using FFmpeg if specified (post-processing approach)
        if hasattr(self, "background_music_info") and self.background_music_info:
            try:
                self.logger.info(
                    "🎵 Applying background music using FFmpeg post-processing..."
                )

                # Create temporary file for the video with background music
                temp_output = output_file.with_suffix(".temp_with_music.mp4")

                # Apply background music using FFmpeg
                if self._apply_background_music_ffmpeg(output_file, temp_output):
                    # Replace original file with the music-enhanced version
                    shutil.move(str(temp_output), str(output_file))
                    self.logger.info(
                        "✅ Background music applied successfully using FFmpeg!"
                    )
                else:
                    self.logger.warning(
                        "⚠️ Failed to apply background music, keeping original video"
                    )
                    if temp_output.exists():
                        temp_output.unlink()

            except Exception as bgm_error:
                self.logger.error(
                    f"❌ Background music post-processing failed: {bgm_error}"
                )
                self.logger.info("🔄 Keeping original video without background music")

        print(f"Video created successfully: {output_file}")
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
