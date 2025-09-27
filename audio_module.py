#!/usr/bin/env python3
"""
VolcEngine Audio Generation Module - Based on Official Demo
Rewritten to use the official volcengine_binary_demo implementation
"""

import os
import json
import logging
import struct
import io
import asyncio
import websockets
import uuid
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from enum import IntEnum

# Import MoviePy components
from moviepy import AudioFileClip, concatenate_audioclips, vfx

# Import the official protocols
import sys
demo_path = Path(__file__).parent / "volcengine_binary_demo"
sys.path.insert(0, str(demo_path))

try:
    from protocols.protocols import MsgType, MsgTypeFlagBits, Message, full_client_request, receive_message  # type: ignore
except ImportError:
    # Fallback implementation if demo not available
    class MsgType(IntEnum):
        """Message type enumeration"""
        Invalid = 0
        FullClientRequest = 0b1
        AudioOnlyClient = 0b10
        FullServerResponse = 0b1001
        AudioOnlyServer = 0b1011
        FrontEndResultServer = 0b1100
        Error = 0b1111

    class MsgTypeFlagBits(IntEnum):
        """Message type flag bits"""
        NoSeq = 0
        PositiveSeq = 0b1
        LastNoSeq = 0b10
        NegativeSeq = 0b11
        WithEvent = 0b100

    @dataclass
    class Message:
        """Simplified Message class for fallback"""
        type: MsgType = MsgType.Invalid
        flag: MsgTypeFlagBits = MsgTypeFlagBits.NoSeq
        sequence: int = 0
        payload: bytes = b""

        @classmethod
        def from_bytes(cls, data: bytes):
            """Simplified from_bytes"""
            if len(data) < 3:
                return cls()

            try:
                type_and_flag = data[1]
                msg_type = MsgType(type_and_flag >> 4)
                flag = MsgTypeFlagBits(type_and_flag & 0x0F)

                msg = cls(type=msg_type, flag=flag)
                msg.unmarshal(data)
                return msg
            except Exception:
                return cls()

        def unmarshal(self, data: bytes):
            """Simplified unmarshal"""
            buffer = io.BytesIO(data)

            # Skip first 3 bytes (header)
            buffer.read(3)

            # Read sequence if present
            if self.flag in [MsgTypeFlagBits.PositiveSeq, MsgTypeFlagBits.NegativeSeq]:
                seq_bytes = buffer.read(4)
                if len(seq_bytes) == 4:
                    self.sequence = struct.unpack(">i", seq_bytes)[0]

            # Read payload
            size_bytes = buffer.read(4)
            if len(size_bytes) == 4:
                payload_size = struct.unpack(">I", size_bytes)[0]
                self.payload = buffer.read(payload_size)

        def marshal(self) -> bytes:
            """Simplified marshal"""
            buffer = io.BytesIO()

            # Write header
            header = [
                (1 << 4) | 1,  # Version 1, HeaderSize 4
                (self.type << 4) | self.flag,
                (1 << 4) | 0,  # JSON serialization, no compression
            ]

            # Add padding
            header.extend([0])  # 4 bytes total

            buffer.write(bytes(header))

            # Write sequence if present
            if self.flag in [MsgTypeFlagBits.PositiveSeq, MsgTypeFlagBits.NegativeSeq]:
                buffer.write(struct.pack(">i", self.sequence))

            # Write payload
            size = len(self.payload)
            buffer.write(struct.pack(">I", size))
            buffer.write(self.payload)

            return buffer.getvalue()

    async def full_client_request(websocket, payload: bytes):
        """Send full client request"""
        msg = Message(type=MsgType.FullClientRequest, flag=MsgTypeFlagBits.NoSeq)
        msg.payload = payload
        await websocket.send(msg.marshal())

    async def receive_message(websocket):
        """Receive message"""
        data = await websocket.recv()
        return Message.from_bytes(data)


class VolcEngineTTSManager:
    """
    VolcEngine TTS Manager - Based on official demo implementation
    """

    def __init__(self, config_manager):
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        self.project_folder = config_manager.project_folder
        self.paths = {
            'project': self.project_folder,
            'media': self.project_folder / "media",
            'prompt': self.project_folder / "prompt",
            'subtitle': self.project_folder / "subtitle",
            'output': self.project_folder / "output"
        }

        # Volcengine settings
        self.app_id = os.getenv("VOLCENGINE_APP_ID")
        self.access_token = os.getenv("VOLCENGINE_ACCESS_TOKEN")

        if not self.app_id or not self.access_token:
            self.logger.error("Volcengine credentials not found in environment variables")
            raise ValueError("Volcengine credentials required")

        # TTS settings
        self.voice_type = "zh_female_shuangkuaisisi_moon_bigtts"
        self.encoding = "mp3"
        self.cluster = "volcano_tts"
        self.endpoint = "wss://openspeech.bytedance.com/api/v1/tts/ws_binary"

    def get_cluster(self, voice: str) -> str:
        """Get cluster based on voice type"""
        if voice.startswith("S_"):
            return "volcano_icl"
        return "volcano_tts"

    async def generate_audio_websocket(self, text: str) -> Optional[bytes]:
        """Generate audio using Volcengine WebSocket API - Based on official demo"""
        headers = {
            "Authorization": f"Bearer;{self.access_token}",
        }

        self.logger.info(f"Connecting to VolcEngine TTS WebSocket: {self.endpoint}")

        try:
            async with websockets.connect(
                self.endpoint,
                additional_headers=headers,
                max_size=10 * 1024 * 1024
            ) as websocket:
                self.logger.info(
                    f"Connected to WebSocket server, Logid: {getattr(getattr(websocket, 'response', None), 'headers', {}).get('x-tt-logid', 'N/A')}"
                )

                # Prepare request payload - exactly like official demo
                request = {
                    "app": {
                        "appid": self.app_id,
                        "token": self.access_token,
                        "cluster": self.cluster,
                    },
                    "user": {
                        "uid": str(uuid.uuid4()),
                    },
                    "audio": {
                        "voice_type": self.voice_type,
                        "encoding": self.encoding,
                    },
                    "request": {
                        "reqid": str(uuid.uuid4()),
                        "text": text,
                        "operation": "submit",
                        "with_timestamp": "1",
                        "extra_param": json.dumps({
                            "disable_markdown_filter": False,
                        }),
                    },
                }

                # Send request using official demo method
                await full_client_request(websocket, json.dumps(request).encode())

                # Receive audio data - exactly like official demo
                audio_data = bytearray()
                message_count = 0

                while True:
                    msg = await receive_message(websocket)
                    message_count += 1

                    # Show progress
                    if message_count % 10 == 0:
                        print(".", end="", flush=True)

                    if msg.type == MsgType.FrontEndResultServer:
                        continue
                    elif msg.type == MsgType.AudioOnlyServer:
                        audio_data.extend(msg.payload)
                        if msg.sequence < 0:  # Last message
                            break
                    else:
                        self.logger.error(f"TTS conversion failed: {msg}")
                        return None

                # Show completion
                print()  # Newline after progress dots

                # Check if we received any audio data
                if not audio_data:
                    self.logger.error("No audio data received")
                    return None

                self.logger.info(f"Audio received: {len(audio_data)} bytes")
                return bytes(audio_data)

        except Exception as e:
            self.logger.error(f"VolcEngine TTS WebSocket error: {e}")
            return None

    async def generate_audio_async(self, subtitles) -> Optional[str]:
        """Generate audio from subtitles using VolcEngine TTS (async version)"""
        if not subtitles:
            self.logger.error("No subtitles provided for audio generation")
            return None

        # Handle different subtitle formats
        if isinstance(subtitles, list):
            if len(subtitles) > 0 and isinstance(subtitles[0], dict):
                # Dictionary format: [{'text': 'subtitle text', ...}, ...]
                full_text = " ".join([sub['text'] for sub in subtitles if 'text' in sub])
            elif len(subtitles) > 0 and isinstance(subtitles[0], str):
                # String format: ['subtitle text', ...]
                full_text = " ".join(subtitles)
            else:
                self.logger.error("Unsupported subtitle format")
                return None
        elif isinstance(subtitles, str):
            # Single string format
            full_text = subtitles
        else:
            self.logger.error("Unsupported subtitle format")
            return None

        self.logger.info(f"Generating audio for text: {full_text[:100]}...")

        try:
            # Generate audio data
            audio_data = await self.generate_audio_websocket(full_text)

            if audio_data:
                # Save audio file
                output_path = self.paths['project'] / "generated_audio.mp3"
                with open(output_path, 'wb') as f:
                    f.write(audio_data)

                self.logger.info(f"Audio generated successfully: {output_path}")
                return str(output_path)
            else:
                self.logger.error("Failed to generate audio")
                return None

        except Exception as e:
            self.logger.error(f"Error generating audio: {e}")
            return None

    def generate_audio(self, subtitles) -> Optional[str]:
        """Generate audio from subtitles using VolcEngine TTS (sync wrapper)"""
        try:
            # Try to get the running event loop
            asyncio.get_running_loop()
            # If we're in a running loop, create a task
            import concurrent.futures

            def run_async():
                # Create a new event loop in a separate thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(self.generate_audio_async(subtitles))
                finally:
                    new_loop.close()

            # Run in a separate thread to avoid event loop conflicts
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async)
                return future.result()

        except RuntimeError:
            # No running event loop, we can use asyncio.run()
            return asyncio.run(self.generate_audio_async(subtitles))

    def load_existing_audio(self) -> Optional[str]:
        """Load existing audio file"""
        audio_path = self.paths['project'] / "generated_audio.mp3"

        if audio_path.exists():
            self.logger.info(f"Found existing audio file: {audio_path}")
            return str(audio_path)

        return None

    def validate_audio_file(self, audio_path: str) -> bool:
        """Validate audio file"""
        if not audio_path or not Path(audio_path).exists():
            return False

        try:
            # Try to get audio duration
            with AudioFileClip(audio_path) as clip:
                duration = clip.duration
                self.logger.info(f"Audio file duration: {duration:.2f}s")
                return duration > 0
        except Exception as e:
            self.logger.error(f"Error validating audio file: {e}")
            return False

    def get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration"""
        try:
            with AudioFileClip(audio_path) as clip:
                return clip.duration
        except Exception as e:
            self.logger.error(f"Error getting audio duration: {e}")
            return 0

    def normalize_audio(self, audio_path: str, output_path: Optional[str] = None) -> Optional[str]:
        """Normalize audio volume"""
        if output_path is None:
            path_obj = Path(audio_path)
            output_path = str(path_obj.parent / f"normalized_{path_obj.name}")

        if not output_path:
            return None

        try:
            with AudioFileClip(audio_path) as clip:
                # Normalize volume - use MultiplyColor for volume
                normalized_clip = clip.with_effects([vfx.MultiplyColor(0.8)])

                # Apply fade in/out - use with_effects for fade
                normalized_clip = normalized_clip.with_effects([vfx.FadeIn(0.1), vfx.FadeOut(0.1)])

                # Export
                normalized_clip.write_audiofile(  # type: ignore
                    output_path,
                    fps=22050,
                    nbytes=2,
                    codec='mp3'
                )

            self.logger.info(f"Audio normalized: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Error normalizing audio: {e}")
            return None

    def create_silent_audio(self, duration: float, output_path: str) -> bool:
        """Create silent audio"""
        try:
            from moviepy import AudioClip
            import numpy as np

            def make_frame(t):
                return np.zeros((2,))

            silent_clip = AudioClip(make_frame, duration=duration, fps=22050)
            silent_clip.write_audiofile(
                output_path,
                fps=22050,
                nbytes=2,
                codec='mp3'
            )

            self.logger.info(f"Silent audio created: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error creating silent audio: {e}")
            return False

    def concatenate_audio_files(self, audio_files: List[str], output_path: str) -> Optional[str]:
        """Concatenate multiple audio files"""
        if not audio_files:
            return None

        try:
            clips = []
            for audio_file in audio_files:
                if Path(audio_file).exists():
                    clip = AudioFileClip(audio_file)
                    clips.append(clip)

            if clips:
                final_clip = concatenate_audioclips(clips)
                final_clip.write_audiofile(  # type: ignore
                    output_path,
                    fps=22050,
                    nbytes=2,
                    codec='mp3'
                )

                self.logger.info(f"Audio files concatenated: {output_path}")
                return output_path
            else:
                self.logger.error("No valid audio files to concatenate")
                return None

        except Exception as e:
            self.logger.error(f"Error concatenating audio files: {e}")
            return None

    def adjust_audio_speed(self, audio_path: str, speed_factor: float, output_path: str) -> Optional[str]:
        """Adjust audio playback speed"""
        try:
            with AudioFileClip(audio_path) as clip:
                # Adjust speed - use MultiplySpeed for speed adjustment
                adjusted_clip = clip.with_effects([vfx.MultiplySpeed(speed_factor)])

                # Export
                adjusted_clip.write_audiofile(  # type: ignore
                    output_path,
                    fps=22050,
                    nbytes=2,
                    codec='mp3'
                )

            self.logger.info(f"Audio speed adjusted: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Error adjusting audio speed: {e}")
            return None

    def add_background_music(self, main_audio_path: str, bg_music_path: str, output_path: str, bg_volume: float = 0.3) -> Optional[str]:
        """Add background music to main audio"""
        try:
            from moviepy import AudioFileClip, CompositeAudioClip

            # Load main audio
            main_clip = AudioFileClip(main_audio_path)

            # Load and adjust background music
            bg_clip = AudioFileClip(bg_music_path)
            bg_clip = bg_clip.with_effects([vfx.MultiplyColor(bg_volume)])

            # Loop background music if needed
            if bg_clip.duration < main_clip.duration:
                # Simple looping approach for MoviePy 2.2.1
                bg_clip = bg_clip.with_effects([vfx.TimeMirror()])  # Placeholder for loop
            else:
                bg_clip = bg_clip.subclipped(0, main_clip.duration)

            # Combine audio
            combined = CompositeAudioClip([main_clip, bg_clip])
            combined.write_audiofile(  # type: ignore
                output_path,
                fps=22050,
                nbytes=2,
                codec='mp3'
            )

            self.logger.info(f"Background music added: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Error adding background music: {e}")
            return None


    def calculate_subtitle_timestamps(self, voice_subtitles, display_subtitles, display_to_voice_mapping, audio_file_path, logger=None):
        """Calculate intelligent timestamps for display subtitles based on voice subtitles and audio duration"""
        if not audio_file_path or not Path(audio_file_path).exists():
            raise ValueError("Audio file not available for timestamp calculation")

        try:
            # Load audio file to get duration
            from moviepy import AudioFileClip
            audio_clip = AudioFileClip(str(audio_file_path))
            total_duration = audio_clip.duration
            audio_clip.close()

            if logger:
                logger.info(f"Audio duration: {total_duration:.2f}s")
                logger.info(f"Voice subtitles: {len(voice_subtitles)}")
                logger.info(f"Display subtitles: {len(display_subtitles)}")

            # Calculate timing based on voice subtitles (with punctuation)
            voice_estimates = []
            total_voice_time = 0

            for voice_subtitle in voice_subtitles:
                estimated_time = self._estimate_speaking_time(voice_subtitle)
                voice_estimates.append(estimated_time)
                total_voice_time += estimated_time

            if logger:
                logger.info(f"Total voice speaking time: {total_voice_time:.2f}s")

            # Adjust voice timing to fit audio duration
            if total_voice_time > total_duration:
                # Scale down to fit
                scale_factor = total_duration / total_voice_time
                if logger:
                    logger.info(f"Scaling voice timing by factor: {scale_factor:.3f}")
                voice_estimates = [time * scale_factor for time in voice_estimates]
            elif total_voice_time < total_duration:
                # Distribute extra time proportionally
                extra_time = total_duration - total_voice_time
                proportional_extra = [extra_time * (time / total_voice_time) for time in voice_estimates]
                voice_estimates = [voice_estimates[i] + proportional_extra[i] for i in range(len(voice_estimates))]

            # Map voice subtitle timing to display subtitles using the mapping
            subtitle_timestamps = []

            # Calculate voice subtitle start times
            voice_start_times = []
            voice_accumulated = 0.0
            for voice_duration in voice_estimates:
                voice_start_times.append(voice_accumulated)
                voice_accumulated += voice_duration

            # Group display subtitles by their original voice subtitle
            display_groups = {}
            for display_idx, voice_idx in display_to_voice_mapping:
                if voice_idx not in display_groups:
                    display_groups[voice_idx] = []
                display_groups[voice_idx].append(display_idx)

            # Calculate timing for each voice subtitle group
            for voice_idx, display_indices in display_groups.items():
                if voice_idx < len(voice_start_times):
                    voice_start = voice_start_times[voice_idx]
                    voice_duration = voice_estimates[voice_idx]

                    if len(display_indices) == 1:
                        # Single display subtitle for this voice subtitle
                        display_idx = display_indices[0]
                        if display_idx < len(display_subtitles):
                            subtitle_timestamps.append({
                                'text': display_subtitles[display_idx],
                                'start_time': voice_start,
                                'end_time': voice_start + voice_duration
                            })
                    else:
                        # Multiple display subtitles for this voice subtitle
                        for i, display_idx in enumerate(display_indices):
                            if display_idx < len(display_subtitles):
                                # Distribute time proportionally among display subtitles
                                ratio = 1.0 / len(display_indices)
                                start_time = voice_start + (i * voice_duration * ratio)
                                end_time = voice_start + ((i + 1) * voice_duration * ratio)

                                subtitle_timestamps.append({
                                    'text': display_subtitles[display_idx],
                                    'start_time': start_time,
                                    'end_time': end_time
                                })

            return subtitle_timestamps

        except Exception as e:
            if logger:
                logger.error(f"Error calculating subtitle timestamps: {e}")
            raise

    def _estimate_speaking_time(self, text):
        """Estimate speaking time based on text content"""
        if not text:
            return 0.0

        # Base calculation: Chinese characters take ~0.4s, English words take ~0.3s
        chinese_count = self._count_chinese_characters(text)
        english_words = len([word for word in text.split() if not any('\u4e00' <= char <= '\u9fff' for char in word)])

        # Calculate estimated time
        chinese_time = chinese_count * 0.4
        english_time = english_words * 0.3

        # Add some buffer for natural pauses
        base_time = chinese_time + english_time
        buffer_time = min(len(text) * 0.01, 2.0)  # Max 2 seconds buffer

        estimated_time = max(base_time + buffer_time, 1.0)  # Minimum 1 second
        return estimated_time

    def _count_chinese_characters(self, text):
        """Count Chinese characters in text"""
        if not text:
            return 0
        return sum(1 for char in text if '\u4e00' <= char <= '\u9fff')


# Backward compatibility - create AudioManager alias
AudioManager = VolcEngineTTSManager