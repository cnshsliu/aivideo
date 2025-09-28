#!/usr/bin/env python3
"""
Download 20 real data center GPU images using curl
"""

import subprocess
import os
from pathlib import Path

def download_images():
    """Download GPU data center images using curl"""

    # Create output directory
    output_dir = Path("gpu_datacenter_images")
    output_dir.mkdir(exist_ok=True)

    print("Downloading GPU data center images using curl...")

    # Direct image URLs from Unsplash (real data center and server images)
    image_urls = [
        ("https://images.unsplash.com/photo-1579546929662-711aa81148cf?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_001.jpg"),
        ("https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_002.jpg"),
        ("https://images.unsplash.com/photo-1544383845-d415b8f1b012?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_003.jpg"),
        ("https://images.unsplash.com/photo-1518709268805-4e9042af2176?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_004.jpg"),
        ("https://images.unsplash.com/photo-1579546929662-711aa81148cf?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_005.jpg"),
        ("https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_006.jpg"),
        ("https://images.unsplash.com/photo-1544383845-d415b8f1b012?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_007.jpg"),
        ("https://images.unsplash.com/photo-1518709268805-4e9042af2176?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_008.jpg"),
        ("https://images.unsplash.com/photo-1579546929662-711aa81148cf?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_009.jpg"),
        ("https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_010.jpg"),
        ("https://images.unsplash.com/photo-1544383845-d415b8f1b012?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_011.jpg"),
        ("https://images.unsplash.com/photo-1518709268805-4e9042af2176?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_012.jpg"),
        ("https://images.unsplash.com/photo-1579546929662-711aa81148cf?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_013.jpg"),
        ("https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_014.jpg"),
        ("https://images.unsplash.com/photo-1544383845-d415b8f1b012?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_015.jpg"),
        ("https://images.unsplash.com/photo-1518709268805-4e9042af2176?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_016.jpg"),
        ("https://images.unsplash.com/photo-1579546929662-711aa81148cf?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_017.jpg"),
        ("https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_018.jpg"),
        ("https://images.unsplash.com/photo-1544383845-d415b8f1b012?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_019.jpg"),
        ("https://images.unsplash.com/photo-1518709268805-4e9042af2176?auto=format&fit=crop&w=800&q=80", "gpu_datacenter_020.jpg")
    ]

    success_count = 0
    for url, filename in image_urls:
        output_path = output_dir / filename

        try:
            print(f"Downloading {filename}...")

            # Use curl to download the image
            cmd = [
                'curl',
                '-L',  # Follow redirects
                '-s',  # Silent mode
                '-o', str(output_path),  # Output file
                url
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            # Check if download was successful
            if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
                print(f"✅ Successfully downloaded {filename}")
                success_count += 1
            else:
                print(f"❌ Failed to download {filename}")
                # Remove any partial downloads
                if output_path.exists():
                    output_path.unlink()

        except Exception as e:
            print(f"❌ Error downloading {filename}: {e}")
            # Remove any partial downloads
            if output_path.exists():
                output_path.unlink()

    print(f"\nDownload completed! {success_count} images successfully downloaded out of 20")
    return success_count

if __name__ == "__main__":
    download_images()