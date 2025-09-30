import logging
from datetime import datetime
from moviepy import (
    TextClip,
    CompositeVideoClip,
)


class TitleProcessor:
    """Handles all subtitle processing operations"""

    def __init__(self, logger=None):
        """Initialize subtitle processor with optional logger"""
        self.logger = logger or logging.getLogger(__name__)

    def _add_title_basic(self, args, clip, title):
        """Add title to clip with Chinese font support

        Args:
            clip: The video clip to add title to
        """
        if not title:
            return clip
        if not clip:
            return clip

        try:
            title_duration = clip.duration

            if args.title_timestamp:
                title = title + "," + datetime.now().strftime("%H:%M:%S")

            # Parse title - split by comma for multi-line
            title_lines = title.split(",")
            font_size = getattr(args, "title_font_size", 60)
            if font_size is None:
                font_size = 60
            title_font = "Hiragino Sans GB"

            title_clips = []
            title_position = getattr(args, "title_position", 20)
            if title_position is None:
                title_position = 20
            y_offset = title_position / 100 * clip.h

            for i, line in enumerate(title_lines):
                current_font_size = font_size if i == 0 else int(font_size * 0.9)

                try:
                    title_clip = TextClip(
                        title_font,
                        line.strip(),
                        font_size=current_font_size,
                        color="yellow",
                        stroke_color="black",
                        stroke_width=4,
                        method="label",
                    )

                    # Position the title
                    if title_clip is not None:
                        title_x = clip.w / 2 - title_clip.w / 2
                        title_y = y_offset + i * (current_font_size + 10)

                        title_clip = title_clip.with_position((title_x, title_y))
                        # Show title only for the specified duration
                        if title_clip is not None:
                            title_clip = title_clip.with_duration(title_duration)
                        title_clips.append(title_clip)
                except Exception as text_error:
                    print(
                        f"Damn, title text clip creation failed for line '{line.strip()}': {text_error}"
                    )

            if not title_clips:
                print("No title clips created, returning original clip")
                return clip

            # Filter out any None clips that might have been created
            title_clips = [aclip for aclip in title_clips if aclip is not None]
            if not title_clips:
                print("All title clips were None, returning original clip")
                return clip

            try:
                all_clips = [clip] + title_clips
                # Filter out any None clips
                all_clips = [c for c in all_clips if c is not None]

                result = CompositeVideoClip(all_clips)
                if clip:
                    result = result.with_duration(clip.duration)
                if result:
                    self.logger.info(f"Title covers entire clip: {result.duration}s")
                return result
            except Exception as composite_error:
                self.logger.error(f"Error during composite creation: {composite_error}")
                # Fallback: return original clip without title
                return clip

        except Exception as e:
            print(f"Damn, title creation failed: {e}")
            self.logger.error(f"Title creation failed: {e}")
            return clip

    def add_title(self, args, clip, title):
        """Add prominent title to clip with enhanced visibility"""
        if not title:
            return clip

        try:
            # TEMPORARY: Disable enhanced title system due to frame read issues
            self.logger.info(
                "Enhanced titles disabled temporarily due to frame read issues, using basic title system"
            )
            return self._add_title_basic(args, clip, title)

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
            return self._add_title_basic(args, clip, title)
