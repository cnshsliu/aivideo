import websockets
import uuid
import struct
import json
import io
import logging
import asyncio
import os
import sys


class AudioGenerator:
    """Handles all audio generation operations"""

    def __init__(self, logger=None):
        """Initialize subtitle processor with optional logger"""
        self.logger = logger or logging.getLogger(__name__)

    def generate_audio(self, vg):
        """Generate audio from subtitles using Volcengine TTS"""
        # Use voice_subtitles (with punctuation) for audio generation
        if not hasattr(vg, "voice_subtitles") or not vg.voice_subtitles:
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
        full_text = "，".join(vg.voice_subtitles)

        try:
            # Generate audio using Volcengine TTS
            audio_path = vg.project_folder / "generated_audio.mp3"

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

            vg.audio_file = audio_path

            # Calculate subtitle timestamps based on audio duration and subtitle count
            vg._calculate_subtitle_timestamps()

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
