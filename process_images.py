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
from PIL import Image, ImageEnhance
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

        Args:
            image: PIL Image object

        Returns:
            PIL Image object with mobile portrait dimensions
        """
        # Store original size
        original_width, original_height = image.size

        # Random transformation parameters
        scale_factor = random.uniform(1.2, 3.0)  # Scale up 1.2x to 3x
        rotation_angle = random.uniform(-45, 45)  # Rotate -45 to +45 degrees

        # Apply transformations
        transformed_image = self._apply_scale_rotate(image, scale_factor, rotation_angle)

        # Random crop to mobile size
        cropped_image = self._random_crop(transformed_image)

        return cropped_image

    def _apply_scale_rotate(self, image, scale_factor, rotation_angle):
        """Apply scaling and rotation to image."""
        # First scale the image
        new_width = int(image.width * scale_factor)
        new_height = int(image.height * scale_factor)

        # Use high-quality resampling
        scaled_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Apply rotation with high-quality resampling and expand to fit rotated image
        if rotation_angle != 0:
            rotated_image = scaled_image.rotate(
                rotation_angle,
                resample=Image.Resampling.BICUBIC,
                expand=True,
                fillcolor=(255, 255, 255)  # White background for rotation
            )
        else:
            rotated_image = scaled_image

        return rotated_image

    def _random_crop(self, image):
        """
        Randomly crop image to mobile portrait dimensions.

        Args:
            image: PIL Image object (larger than output size)

        Returns:
            PIL Image object cropped to output_size
        """
        img_width, img_height = image.size

        # Ensure image is large enough for cropping
        if img_width < self.output_width or img_height < self.output_height:
            logger.warning(f"Image {image.size} is too small for {self.output_size}, will scale up")
            image = image.resize(self.output_size, Image.Resampling.LANCZOS)
            return image

        # Calculate random crop position
        max_x = img_width - self.output_width
        max_y = img_height - self.output_height

        crop_x = random.randint(0, max_x)
        crop_y = random.randint(0, max_y)

        # Perform crop
        crop_box = (crop_x, crop_y, crop_x + self.output_width, crop_y + self.output_height)
        cropped_image = image.crop(crop_box)

        return cropped_image

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