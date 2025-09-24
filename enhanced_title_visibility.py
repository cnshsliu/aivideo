#!/usr/bin/env python3
"""
Enhanced Title Visibility Module - Practical implementation for video generator
Makes titles prominent and readable on any background using proven techniques
"""

import logging
from moviepy.editor import TextClip, ColorClip, CompositeVideoClip

# Set up logging
logger = logging.getLogger(__name__)

def create_prominent_title_clip(text, fontsize=72, font='Arial-Unicode-MS', 
                               position=('center', 20), duration=None,
                               effect_strength='medium'):
    """
    Create a title clip that's highly visible on any background
    
    Techniques used:
    1. Thick black outline (stroke)
    2. Drop shadow
    3. Semi-transparent background box
    4. High contrast colors
    
    Args:
        text: Title text (supports Chinese)
        fontsize: Font size
        font: Font name (should support Chinese)
        position: (horizontal, vertical_percent) - e.g., ('center', 20)
        duration: Clip duration in seconds
        effect_strength: 'light', 'medium', or 'heavy' for effect intensity
        
    Returns:
        CompositeVideoClip with highly visible title
    """
    
    # Validate inputs
    if not text or not text.strip():
        logger.warning("Empty title text provided")
        return None
    
    # Set effect parameters based on strength
    params = {
        'light': {'outline_width': 1, 'shadow_offset': 2, 'box_opacity': 0.5},
        'medium': {'outline_width': 3, 'shadow_offset': 4, 'box_opacity': 0.7},
        'heavy': {'outline_width': 5, 'shadow_offset': 6, 'box_opacity': 0.85}
    }
    
    p = params.get(effect_strength, params['medium'])
    
    try:
        # Create the main text with thick outline
        main_text = TextClip(
            text.strip(),
            fontsize=fontsize,
            font=font,
            color='white',  # Bright white text
            stroke_color='black',  # Black outline for contrast
            stroke_width=p['outline_width'],
            method='label'  # Efficient rendering method
        )
        
        # Create drop shadow
        shadow = TextClip(
            text.strip(),
            fontsize=fontsize,
            font=font,
            color='black'  # Black shadow
        ).set_position((p['shadow_offset'], p['shadow_offset']))
        
        # Create semi-transparent background box
        padding = fontsize // 3  # Dynamic padding based on font size
        box = ColorClip(
            size=(main_text.w + padding*2, main_text.h + padding*2),
            color=(0, 0, 0)  # Black background
        ).set_opacity(p['box_opacity'])
        
        # Position main text in center of background box
        main_text = main_text.set_position(('center', 'center'))
        shadow = shadow.set_position(('center', 'center'))
        
        # Create final composite with background box + shadow + text
        final_clip = CompositeVideoClip([
            box,      # Background box (bottom layer)
            shadow,   # Drop shadow (middle layer)
            main_text # Main text (top layer)
        ])
        
        # Set position on screen
        if position[0] == 'center':
            x_pos = 'center'
        else:
            x_pos = position[0]
            
        y_pos = f"{position[1]}%"
        
        final_clip = final_clip.set_position((x_pos, y_pos))
        
        # Set duration if provided
        if duration:
            final_clip = final_clip.set_duration(duration)
            
        logger.info(f"Created prominent title: '{text[:20]}...' "
                   f"[{main_text.w}x{main_text.h}] with {effect_strength} effects")
        
        return final_clip
        
    except Exception as e:
        logger.error(f"Failed to create prominent title '{text}': {e}")
        # Fallback: create basic title
        try:
            basic_title = TextClip(
                text.strip(),
                fontsize=fontsize,
                font=font,
                color='white',
                stroke_color='black',
                stroke_width=1
            )
            
            if duration:
                basic_title = basic_title.set_duration(duration)
                
            logger.info(f"Created fallback basic title for '{text[:20]}...'")
            return basic_title
            
        except Exception as fallback_error:
            logger.error(f"Fallback title creation also failed: {fallback_error}")
            return None

def add_prominent_title_to_clip(video_clip, title_text, args=None):
    """
    Add a highly visible title to a video clip
    
    This is the main integration function for the video generator
    
    Args:
        video_clip: The base video clip to add title to
        title_text: The title text to display
        args: Optional command line arguments for customization
        
    Returns:
        Video clip with prominent title added
    """
    
    # Get parameters from args or use defaults
    if args:
        fontsize = getattr(args, 'title_font_size', 72) or 72
        font = getattr(args, 'title_font', 'Arial-Unicode-MS') or 'Arial-Unicode-MS'
        position_percent = getattr(args, 'title_position', 20) or 20
        effect_strength = getattr(args, 'title_effect_strength', 'medium')
    else:
        fontsize = 72
        font = 'Arial-Unicode-MS'
        position_percent = 20
        effect_strength = 'medium'
    
    # Create the prominent title
    title_clip = create_prominent_title_clip(
        text=title_text,
        fontsize=fontsize,
        font=font,
        position=('center', position_percent),
        duration=video_clip.duration,  # Title covers entire clip
        effect_strength=effect_strength
    )
    
    if title_clip is None:
        logger.warning(f"Failed to create title for: '{title_text}'")
        return video_clip
    
    try:
        # Composite the title onto the video
        final_clip = CompositeVideoClip([video_clip, title_clip])
        
        # Preserve original duration
        final_clip = final_clip.set_duration(video_clip.duration)
        
        logger.info(f"Successfully added prominent title: '{title_text[:20]}...'")
        
        # Clean up the title clip
        title_clip.close()
        
        return final_clip
        
    except Exception as e:
        logger.error(f"Failed to composite title onto video: {e}")
        title_clip.close()
        return video_clip

def demo_title_effects():
    """Demonstrate different title effect strengths"""
    print("Title Effect Strength Demo")
    print("=" * 30)
    
    test_text = "测试标题效果"
    
    for strength in ['light', 'medium', 'heavy']:
        print(f"\n{strength.upper()} effect:")
        clip = create_prominent_title_clip(
            text=test_text,
            fontsize=60,
            effect_strength=strength,
            duration=3.0
        )
        
        if clip:
            print(f"  ✓ Created {strength} effect title: {clip.w}x{clip.h}")
            clip.close()
        else:
            print(f"  ✗ Failed to create {strength} effect title")

if __name__ == "__main__":
    demo_title_effects()