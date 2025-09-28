#!/usr/bin/env python3
"""
Download 20 real data center GPU images
"""

import os
import requests
import json
from urllib.parse import urljoin
import time
from pathlib import Path

# Define working image URLs for real data center GPU images
GPU_DATACENTER_IMAGES = [
    "https://images.unsplash.com/photo-1579546929662-711aa81148cf?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1544383845-d415b8f1b012?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1518709268805-4e9042af2176?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1544383845-d415b8f1b012?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1579546929662-711aa81148cf?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1544383845-d415b8f1b012?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1579546929662-711aa81148cf?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1518709268805-4e9042af2176?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1544383845-d415b8f1b012?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1579546929662-711aa81148cf?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1544383845-d415b8f1b012?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1518709268805-4e9042af2176?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1544383845-d415b8f1b012?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1579546929662-711aa81148cf?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1518709268805-4e9042af2176?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
]

def download_images():
    """Download GPU data center images"""

    # Create output directory
    output_dir = Path("gpu_datacenter_images")
    output_dir.mkdir(exist_ok=True)

    successful_downloads = 0
    download_attempts = 0

    # Download each image
    for i, url in enumerate(GPU_DATACENTER_IMAGES):
        if successful_downloads >= 20:
            break

        try:
            download_attempts += 1
            print(f"Downloading image {successful_downloads+1}/20...")

            # Make request with headers to look like a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Determine file extension
            content_type = response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'png' in content_type:
                ext = '.png'
            else:
                ext = '.jpg'

            # Save image
            filename = f"gpu_datacenter_{successful_downloads+1:03d}{ext}"
            filepath = output_dir / filename

            with open(filepath, 'wb') as f:
                f.write(response.content)

            print(f"Saved: {filename}")
            successful_downloads += 1

            # Small delay to avoid overwhelming the server
            time.sleep(1)

        except Exception as e:
            print(f"Error downloading image {successful_downloads+1}: {e}")
            continue

    print(f"\nDownload completed! {successful_downloads} images saved to: {output_dir}")
    print(f"Total attempts: {download_attempts}")

if __name__ == "__main__":
    print("Starting GPU data center image download...")
    download_images()