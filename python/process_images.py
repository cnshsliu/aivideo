#!/usr/bin/env python3
"""
Image Processing Script
Randomly transforms images (scale, rotate, crop) and outputs mobile-sized vertical images.

Usage: python process_images.py --folder PATH [--output_dir PATH] [--num_images INT]
"""

import os
import sys
import argparse
import random
import numpy as np
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self, output_width=1080, output_height=1920):
        """
        Initialize image processor with mobile phone vertical screen dimensions.

        Args:
            output_width: Output image width (default: 1080 - mobile portrait width)
            output_height: Output image height (default: 1920 - mobile portrait height)
        """
        self.output_width = output_width
        self.output_height = output_height
        self.output_size = (output_width, output_height)

    def random_transform(self, image):
        """
        Apply random transformations to image and return mobile-sized result.

        New balanced approach:
        1. First rotate the image randomly and scale to ensure minimum dimensions
        2. Then iteratively crop and check for white corners, scaling up gradually
        3. Stop when no white corners are detected

        Args:
            image: PIL Image object

        Returns:
            PIL Image object with mobile portrait dimensions
        """
        # Random rotation angle
        rotation_angle = random.uniform(-45, 45)  # Rotate -45 to +45 degrees

        # Random initial scale factor (1.2 to 3.0)
        initial_scale_factor = random.uniform(1.2, 3.0)

        # Step 1: Apply rotation and initial scaling
        scaled_rotated_image = self._apply_rotation_and_scale(image, rotation_angle, initial_scale_factor)

        # Step 2: Iteratively crop and adjust until no white corners
        mobile_image = self._iterative_crop_until_clean(scaled_rotated_image)

        # Step 3: Apply comprehensive quality enhancement
        enhanced_image = self.enhance_image_quality(mobile_image)

        return enhanced_image

    def _apply_rotation_only(self, image, rotation_angle):
        """Apply rotation to image with white background."""
        if rotation_angle == 0:
            return image

        # Rotate with expand to get the full rotated image
        rotated_image = image.rotate(
            rotation_angle,
            resample=Image.Resampling.BICUBIC,
            expand=True,
            fillcolor=(255, 255, 255)  # White background for rotation
        )

        logger.debug(f"Rotation: {rotation_angle}°, Original: {image.size}, Rotated: {rotated_image.size}")
        return rotated_image

    def _apply_rotation_and_scale(self, image, rotation_angle, scale_factor):
        """
        Apply rotation and scaling to ensure minimum dimensions.

        Args:
            image: PIL Image object
            rotation_angle: Rotation angle in degrees
            scale_factor: Initial scale factor

        Returns:
            PIL Image object that's been rotated and scaled
        """
        # First apply rotation
        rotated_image = self._apply_rotation_only(image, rotation_angle)

        # Calculate required scale to ensure minimum dimensions after rotation
        rotated_width, rotated_height = rotated_image.size
        target_width, target_height = self.output_size

        # Calculate the minimum scale needed to ensure the image can cover the target
        scale_needed_width = target_width / rotated_width if rotated_width > 0 else 1
        scale_needed_height = target_height / rotated_height if rotated_height > 0 else 1
        min_scale_needed = max(scale_needed_width, scale_needed_height)

        # Use the larger of the random scale factor and the minimum needed scale
        final_scale_factor = max(scale_factor, min_scale_needed)

        # Apply scaling
        new_width = int(rotated_width * final_scale_factor)
        new_height = int(rotated_height * final_scale_factor)

        scaled_image = rotated_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        logger.debug(f"Scale: {final_scale_factor:.2f}x, Rotated: {rotated_image.size}, Scaled: {scaled_image.size}")
        return scaled_image

    def _calculate_max_crop_area(self, image, target_aspect_ratio):
        """
        Calculate the maximum crop area that avoids rotation whitespace.

        Args:
            image: PIL Image object (after rotation)
            target_aspect_ratio: Desired aspect ratio (width/height)

        Returns:
            tuple: (max_width, max_height) of the largest crop area
        """
        img_width, img_height = image.size
        img_aspect = img_width / img_height

        # For rotated rectangles, we need to be extremely conservative
        # The safe area is much smaller than the visible area

        # Use the smaller dimension as the base for safety
        smaller_dim = min(img_width, img_height)
        larger_dim = max(img_width, img_height)

        # For rotations up to 45 degrees, the safe area is significantly reduced
        # Use even more conservative estimate: 30% of the smaller dimension
        safe_dimension = int(smaller_dim * 0.3)

        # Calculate crop dimensions based on target aspect ratio
        if target_aspect_ratio < 1.0:  # Portrait orientation
            # For portrait, limit height more than width
            max_height = safe_dimension
            max_width = int(max_height * target_aspect_ratio)
        else:
            # For landscape, limit width more than height
            max_width = safe_dimension
            max_height = int(max_width / target_aspect_ratio)

        # Additional safety factor for rotation whitespace
        safety_factor = 0.7  # Reduce by 30% to be extremely safe
        max_width = int(max_width * safety_factor)
        max_height = int(max_height * safety_factor)

        # For very wide or very tall images, be even more conservative
        if img_aspect > 2.0 or img_aspect < 0.5:  # Very wide or very tall
            extreme_safety = 0.5  # Additional 50% reduction
            max_width = int(max_width * extreme_safety)
            max_height = int(max_height * extreme_safety)

        # For large images (over 2000px in any dimension), be extra conservative
        if larger_dim > 2000:
            large_image_safety = 0.8  # Additional 20% reduction
            max_width = int(max_width * large_image_safety)
            max_height = int(max_height * large_image_safety)

        # Ensure minimum size to avoid too small crops
        min_size = min(img_width, img_height) // 10  # More conservative minimum
        max_width = max(max_width, min_size)
        max_height = max(max_height, min_size)

        # Ensure we don't exceed image dimensions
        max_width = min(max_width, img_width)
        max_height = min(max_height, img_height)

        return max_width, max_height

    def _crop_to_mobile_aspect(self, image):
        """
        Crop image to mobile aspect ratio from center, avoiding rotation whitespace.

        Args:
            image: PIL Image object (after rotation)

        Returns:
            PIL Image object with mobile aspect ratio
        """
        img_width, img_height = image.size
        target_aspect = self.output_width / self.output_height

        # Calculate maximum safe crop area
        crop_width, crop_height = self._calculate_max_crop_area(image, target_aspect)

        # Ensure crop area is not larger than the image
        crop_width = min(crop_width, img_width)
        crop_height = min(crop_height, img_height)

        # Calculate center crop coordinates
        left = (img_width - crop_width) // 2
        top = (img_height - crop_height) // 2
        right = left + crop_width
        bottom = top + crop_height

        # Perform the center crop
        cropped_image = image.crop((left, top, right, bottom))

        logger.debug(f"Crop: Original={image.size}, Crop=({crop_width}x{crop_height}), Final={cropped_image.size}")
        return cropped_image

    def _scale_to_mobile_size(self, image):
        """
        Scale image to final mobile dimensions.

        Args:
            image: PIL Image object (already cropped to correct aspect ratio)

        Returns:
            PIL Image object with mobile portrait dimensions
        """
        # Since the image is already at the correct aspect ratio, we can directly resize
        final_image = image.resize(self.output_size, Image.Resampling.LANCZOS)

        logger.debug(f"Scale: Original={image.size}, Final={final_image.size}")
        return final_image

    def _resize_to_mobile_aspect_ratio(self, image):
        """
        Resize image to mobile dimensions using cover-to-fill approach.

        First scales up the image until it can fully cover the mobile screen,
        then crops to fill the entire screen without black bars.

        Args:
            image: PIL Image object

        Returns:
            PIL Image object with mobile portrait dimensions (1080x1920)
        """
        img_width, img_height = image.size
        target_width, target_height = self.output_size

        # Calculate aspect ratios
        img_aspect = img_width / img_height
        target_aspect = target_width / target_height

        if img_aspect > target_aspect:
            # Image is wider than target - scale to match height, then crop width
            scale_factor = target_height / img_height
            scaled_width = int(img_width * scale_factor)
            scaled_height = target_height

            # Resize the image
            scaled_img = image.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)

            # Calculate crop coordinates (center crop)
            crop_width = target_width
            crop_height = target_height
            left = (scaled_width - crop_width) // 2
            top = 0
            right = left + crop_width
            bottom = top + crop_height

        else:
            # Image is taller than target - scale to match width, then crop height
            scale_factor = target_width / img_width
            scaled_width = target_width
            scaled_height = int(img_height * scale_factor)

            # Resize the image
            scaled_img = image.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)

            # Calculate crop coordinates (center crop)
            crop_width = target_width
            crop_height = target_height
            left = 0
            top = (scaled_height - crop_height) // 2
            right = left + crop_width
            bottom = top + crop_height

        # Perform the center crop
        final_img = scaled_img.crop((left, top, right, bottom))

        logger.debug(f"Original: {image.size} -> Scaled: {scaled_img.size} -> Final: {final_img.size}")

        return final_img

    def _iterative_crop_until_clean(self, scaled_rotated_image):
        """
        Iteratively crop and check for white corners, scaling up gradually.

        Args:
            scaled_rotated_image: PIL Image object (already rotated and scaled)

        Returns:
            PIL Image object with mobile portrait dimensions and no white corners
        """
        current_image = scaled_rotated_image
        target_width, target_height = self.output_size
        max_iterations = 10  # Prevent infinite loops
        scale_increment = 1.1  # 10% scale increase per iteration

        for iteration in range(max_iterations):
            # Try to crop the target size from center
            crop_result = self._center_crop_to_size(current_image, target_width, target_height)

            # Check if the crop has white corners
            if not self._has_white_corners(crop_result):
                logger.debug(f"No white corners found on iteration {iteration}")
                return crop_result

            # If white corners detected, scale up the image and try again
            if iteration < max_iterations - 1:  # Don't scale on the last iteration
                new_width = int(current_image.width * scale_increment)
                new_height = int(current_image.height * scale_increment)
                current_image = current_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.debug(f"Iteration {iteration}: White corners detected, scaled to {new_width}x{new_height}")

        # If we reached max iterations, return the best crop we have
        logger.warning(f"Max iterations reached, returning crop that may have white corners")
        return self._center_crop_to_size(current_image, target_width, target_height)

    def _center_crop_to_size(self, image, target_width, target_height):
        """
        Crop image to exact target size from center.

        Args:
            image: PIL Image object
            target_width: Target width
            target_height: Target height

        Returns:
            PIL Image object with exact target dimensions
        """
        img_width, img_height = image.size

        # Calculate crop coordinates (center crop)
        left = (img_width - target_width) // 2
        top = (img_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height

        # Ensure coordinates are within bounds
        left = max(0, left)
        top = max(0, top)
        right = min(img_width, right)
        bottom = min(img_height, bottom)

        # Perform the crop
        cropped_image = image.crop((left, top, right, bottom))

        # If the crop resulted in wrong dimensions (due to bounds), resize to ensure consistency
        if cropped_image.size != (target_width, target_height):
            cropped_image = cropped_image.resize((target_width, target_height), Image.Resampling.LANCZOS)

        return cropped_image

    def _has_white_corners(self, image, threshold=250):
        """
        Check if image has white corners.

        Args:
            image: PIL Image object
            threshold: RGB threshold for white detection

        Returns:
            bool: True if white corners detected
        """
        import numpy as np

        # Convert to numpy array for corner analysis
        img_array = np.array(image)

        # Check corners for white pixels
        def is_white(pixel, threshold=250):
            return all(p >= threshold for p in pixel)

        # Check all four corners
        corner_colors = [
            img_array[0, 0],      # top-left
            img_array[0, -1],     # top-right
            img_array[-1, 0],    # bottom-left
            img_array[-1, -1]    # bottom-right
        ]

        # Count white corners
        white_corner_count = sum(1 for color in corner_colors if is_white(color, threshold))

        # Consider having white corners if 2 or more corners are white
        return white_corner_count >= 2

    def enhance_image_quality(self, image):
        """
        Apply comprehensive image quality enhancement.

        Includes:
        - Sharpening: Enhance edge clarity
        - Contrast optimization: Auto-adjust contrast
        - Noise reduction: Reduce scaling artifacts
        - Color enhancement: Optimize saturation and vibrance

        Args:
            image: PIL Image object

        Returns:
            PIL Image object with enhanced quality
        """
        enhanced_image = image.copy()

        # Step 1: Apply sharpening
        enhanced_image = self._apply_sharpening(enhanced_image)

        # Step 2: Optimize contrast
        enhanced_image = self._optimize_contrast(enhanced_image)

        # Step 3: Reduce noise
        enhanced_image = self._reduce_noise(enhanced_image)

        # Step 4: Enhance colors
        enhanced_image = self._enhance_colors(enhanced_image)

        logger.debug(f"Image quality enhancement completed")
        return enhanced_image

    def _apply_sharpening(self, image):
        """
        Apply adaptive sharpening to enhance edge clarity.

        Args:
            image: PIL Image object

        Returns:
            PIL Image object with sharpened details
        """
        # Calculate image content complexity to determine sharpening intensity
        import numpy as np
        img_array = np.array(image.convert('L'))  # Convert to grayscale for analysis

        # Calculate standard deviation as a measure of image complexity
        std_dev = np.std(img_array)

        # Adaptive sharpening intensity based on image complexity
        if std_dev < 30:  # Low detail image
            sharpen_factor = 1.3
        elif std_dev < 60:  # Medium detail image
            sharpen_factor = 1.5
        else:  # High detail image
            sharpen_factor = 1.8

        # Apply sharpening using PIL's Unsharp Mask
        enhancer = ImageEnhance.Sharpness(image)
        sharpened = enhancer.enhance(sharpen_factor)

        logger.debug(f"Applied sharpening (factor: {sharpen_factor:.1f}, std_dev: {std_dev:.1f})")
        return sharpened

    def _optimize_contrast(self, image):
        """
        Automatically optimize image contrast using histogram analysis.

        Args:
            image: PIL Image object

        Returns:
            PIL Image object with optimized contrast
        """
        import numpy as np

        # Convert to numpy array for histogram analysis
        img_array = np.array(image)

        # Calculate current contrast using standard deviation
        if len(img_array.shape) == 3:  # RGB image
            gray = np.dot(img_array[...,:3], [0.2989, 0.5870, 0.1140])
        else:
            gray = img_array

        current_contrast = np.std(gray)

        # Target contrast range
        target_min_contrast = 40
        target_max_contrast = 80

        # Calculate contrast enhancement factor
        if current_contrast < target_min_contrast:
            # Low contrast image - needs significant enhancement
            contrast_factor = min(1.4, target_min_contrast / current_contrast * 0.8)
        elif current_contrast > target_max_contrast:
            # High contrast image - mild enhancement or slight reduction
            contrast_factor = 1.1
        else:
            # Medium contrast image - gentle enhancement
            contrast_factor = 1.2

        # Apply contrast enhancement
        enhancer = ImageEnhance.Contrast(image)
        enhanced = enhancer.enhance(contrast_factor)

        logger.debug(f"Optimized contrast (factor: {contrast_factor:.2f}, current: {current_contrast:.1f})")
        return enhanced

    def _reduce_noise(self, image):
        """
        Apply noise reduction to minimize scaling and compression artifacts.

        Args:
            image: PIL Image object

        Returns:
            PIL Image object with reduced noise
        """
        # Apply gentle Gaussian blur for noise reduction
        # Use different radius based on image size
        img_width, img_height = image.size

        if max(img_width, img_height) > 2000:
            blur_radius = 0.8
        elif max(img_width, img_height) > 1000:
            blur_radius = 0.6
        else:
            blur_radius = 0.4

        # Apply very gentle blur for noise reduction
        blurred = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        # Blend original and blurred to preserve details while reducing noise
        # Use 80% original + 20% blurred for subtle noise reduction
        from PIL import ImageChops
        reduced_noise = Image.blend(image, blurred, alpha=0.2)

        logger.debug(f"Applied noise reduction (radius: {blur_radius:.1f})")
        return reduced_noise

    def _enhance_colors(self, image):
        """
        Enhance color saturation and vibrance.

        Args:
            image: PIL Image object

        Returns:
            PIL Image object with enhanced colors
        """
        # Calculate current color saturation
        import numpy as np
        img_array = np.array(image)

        if len(img_array.shape) == 3:  # RGB image
            # Convert to HSV for better color analysis
            hsv = self._rgb_to_hsv(img_array)
            saturation = hsv[:, :, 1]

            # Calculate average saturation
            avg_saturation = np.mean(saturation)

            # Adaptive saturation enhancement based on current saturation
            if avg_saturation < 0.3:  # Low saturation image
                saturation_factor = 1.4
            elif avg_saturation < 0.6:  # Medium saturation image
                saturation_factor = 1.2
            else:  # High saturation image
                saturation_factor = 1.1

            # Apply saturation enhancement
            enhancer = ImageEnhance.Color(image)
            enhanced = enhancer.enhance(saturation_factor)

            # Apply subtle vibrance enhancement (preserve skin tones)
            enhanced = self._apply_vibrance(enhanced, 1.1)

            logger.debug(f"Enhanced colors (saturation: {saturation_factor:.2f}, avg_sat: {avg_saturation:.2f})")
            return enhanced
        else:
            # Grayscale image - no color enhancement needed
            return image

    def _rgb_to_hsv(self, rgb_array):
        """
        Convert RGB array to HSV array.

        Args:
            rgb_array: numpy array in RGB format

        Returns:
            numpy array in HSV format
        """
        # Normalize RGB values to 0-1 range
        rgb = rgb_array.astype(np.float32) / 255.0

        # Extract RGB channels
        r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]

        # Find max and min values
        max_val = np.max(rgb, axis=2)
        min_val = np.min(rgb, axis=2)
        diff = max_val - min_val

        # Calculate saturation
        saturation = np.where(max_val == 0, 0, diff / max_val)

        # Create HSV array
        hsv = np.zeros_like(rgb)
        # Calculate hue (simplified calculation)
        hsv[:, :, 0] = np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b) / (2 * np.pi) + 0.5
        hsv[:, :, 1] = saturation
        hsv[:, :, 2] = max_val

        return hsv

    def _apply_vibrance(self, image, vibrance_factor=1.1):
        """
        Apply vibrance enhancement that preserves skin tones.

        Args:
            image: PIL Image object
            vibrance_factor: Vibrance enhancement factor

        Returns:
            PIL Image object with enhanced vibrance
        """
        import numpy as np
        img_array = np.array(image)

        if len(img_array.shape) == 3:
            # Convert to float for calculations
            rgb = img_array.astype(np.float32) / 255.0

            # Calculate luminance
            luminance = 0.2989 * rgb[:, :, 0] + 0.5870 * rgb[:, :, 1] + 0.1140 * rgb[:, :, 2]

            # Calculate average color values
            avg_color = np.mean(rgb, axis=2)

            # Enhance less saturated colors more (protect skin tones)
            saturation_mask = np.abs(rgb - avg_color[:, :, np.newaxis])
            protection_factor = 1.0 - np.mean(saturation_mask, axis=2) * 0.5

            # Apply vibrance enhancement
            enhanced_rgb = rgb + (rgb - luminance[:, :, np.newaxis]) * (vibrance_factor - 1.0) * protection_factor[:, :, np.newaxis]

            # Clip values to valid range
            enhanced_rgb = np.clip(enhanced_rgb, 0, 1)

            # Convert back to PIL Image
            enhanced_array = (enhanced_rgb * 255).astype(np.uint8)
            enhanced = Image.fromarray(enhanced_array)

            return enhanced
        else:
            return image

    def process_single_image(self, input_path, output_path):
        """
        Process a single image with random transformations.

        Args:
            input_path: Path to input image
            output_path: Path to save processed image

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load image
            with Image.open(input_path) as img:
                # Convert to RGB if necessary (for JPEG compatibility)
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Apply random transformations
                processed_img = self.random_transform(img)

                # Ensure output directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Save processed image
                processed_img.save(output_path, 'JPEG', quality=95)

                logger.info(f"Processed: {input_path.name} -> {output_path.name}")
                return True

        except Exception as e:
            logger.error(f"Error processing {input_path}: {str(e)}")
            return False

    def generate_multiple_variations(self, input_path, output_dir, num_variations=5):
        """
        Generate multiple random variations from a single image.

        Args:
            input_path: Path to input image
            output_dir: Directory to save variations
            num_variations: Number of variations to generate

        Returns:
            int: Number of successfully generated variations
        """
        successful = 0

        for i in range(num_variations):
            # Create output filename with variation number
            input_stem = input_path.stem
            output_filename = f"{input_stem}_var_{i+1:02d}.jpg"
            output_path = output_dir / output_filename

            if self.process_single_image(input_path, output_path):
                successful += 1

        return successful

def find_image_files(directory):
    """
    Find all image files in directory.

    Args:
        directory: Path to search for images

    Returns:
        list: List of Path objects for image files
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    image_files = []

    try:
        directory_path = Path(directory)
        if not directory_path.exists():
            logger.error(f"Directory does not exist: {directory}")
            return image_files

        for ext in image_extensions:
            image_files.extend(directory_path.glob(f"*{ext}"))
            image_files.extend(directory_path.glob(f"*{ext.upper()}"))

        logger.info(f"Found {len(image_files)} image files in {directory}")
        return sorted(image_files)

    except Exception as e:
        logger.error(f"Error searching directory {directory}: {str(e)}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Process images with random transformations")
    parser.add_argument("--folder", required=True,
                       help="Project folder containing 'raw' subdirectory (required)")
    parser.add_argument("--output_dir", default="/tmp/processed_images",
                       help="Output directory for processed images (default: /tmp/processed_images)")
    parser.add_argument("--num_images", type=int, default=5,
                       help="Number of variations to generate per input image (default: 5)")
    parser.add_argument("--width", type=int, default=1080,
                       help="Output width in pixels (default: 1080)")
    parser.add_argument("--height", type=int, default=1920,
                       help="Output height in pixels (default: 1920)")

    args = parser.parse_args()

    # Set up paths
    project_folder = Path(args.folder)
    raw_dir = project_folder / "raw"
    output_dir = Path(args.output_dir)

    # Initialize processor
    processor = ImageProcessor(args.width, args.height)

    # Find input images
    input_images = find_image_files(raw_dir)

    if not input_images:
        logger.error(f"No images found in {raw_dir}")
        logger.info("Please create a 'raw' subdirectory in your project folder and add some images.")
        sys.exit(1)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Process images
    total_generated = 0

    for image_path in input_images:
        logger.info(f"Processing {image_path.name}...")
        generated = processor.generate_multiple_variations(
            image_path, output_dir, args.num_images
        )
        total_generated += generated

        if generated == 0:
            logger.warning(f"Failed to generate variations for {image_path.name}")

    logger.info(f"Image processing complete!")
    logger.info(f"Input images: {len(input_images)}")
    logger.info(f"Generated variations: {total_generated}")
    logger.info(f"Output directory: {output_dir}")

    if total_generated > 0:
        print(f"\n✅ Successfully generated {total_generated} mobile-sized images!")
        print(f"📁 Output saved to: {output_dir}")
    else:
        print("❌ No images were generated successfully.")

if __name__ == "__main__":
    main()