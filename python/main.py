#!/usr/bin/env python3
"""
AI Video Generator - Command line tool for creating videos from media materials
Damn, this is gonna be one hell of a video generator! Don't f*cking pass invalid parameters!
"""

import sys
from typing import TypeVar

# Import configuration module
from config_module import parse_args


from videoGenerator import VideoGenerator

# Type annotations for MoviePy objects
ClipType = TypeVar("ClipType")
VideoClipType = TypeVar("VideoClipType")
TextClipType = TypeVar("TextClipType")
ImageClipType = TypeVar("ImageClipType")
CompositeVideoClipType = TypeVar("CompositeVideoClipType")
AudioClipType = TypeVar("AudioClipType")


def main():
    """Main function - let's get this show on the road!"""
    try:
        args = parse_args()

        # Check if repeatmode is provided (required parameter)
        if not hasattr(args, 'repeatmode') or args.repeatmode is None:
            print("Damn, --repeatmode is required! Please specify --repeatmode single or --repeatmode batch")
            sys.exit(1)
        else:
            print(f"Repeat mode: {args.repeatmode}")

        generator = VideoGenerator(args)
        generator.create_final_video()
    except Exception as e:
        print(f"Damn, video generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
