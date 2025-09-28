#!/usr/bin/env python3
"""
Download 20 real data center GPU images using aria2c for better performance
"""

import subprocess
import os
from pathlib import Path

def download_images():
    """Download GPU data center images using aria2c"""

    # Create output directory
    output_dir = Path("gpu_datacenter_images")
    output_dir.mkdir(exist_ok=True)

    print("Downloading GPU data center images using aria2c...")

    # Create URLs for GPU data center images
    urls = []
    for i in range(20):
        # Different search terms to get variety of GPU data center images
        if i < 5:
            search_term = "gpu+server+rack"
        elif i < 10:
            search_term = "datacenter+gpu+cluster"
        elif i < 15:
            search_term = "nvidia+a100+datacenter"
        else:
            search_term = "gpu+computing+infrastructure"

        url = f"https://source.unsplash.com/800x600/?{search_term}"
        urls.append(url)

    # Create aria2c input file
    input_file = "download_urls.txt"
    with open(input_file, 'w') as f:
        for i, url in enumerate(urls):
            filename = f"gpu_datacenter_{i+1:03d}.jpg"
            f.write(f"{url}\n")
            f.write(f"  out={filename}\n")

    try:
        # Run aria2c with the input file
        cmd = [
            'aria2c',
            '-i', input_file,
            '-d', str(output_dir),
            '-x', '16',  # Max connections per server
            '-s', '16',  # Max connections
            '-j', '20',  # Max concurrent downloads
            '--auto-file-renaming=false',
            '--continue=true',
            '--max-tries=3',
            '--timeout=30'
        ]

        print(f"Starting download of {len(urls)} images...")
        subprocess.run(cmd, check=True)
        print("✅ Download completed successfully!")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error during download: {e}")
    finally:
        # Clean up input file
        if os.path.exists(input_file):
            os.remove(input_file)

if __name__ == "__main__":
    download_images()