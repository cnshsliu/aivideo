#!/usr/bin/env python3
"""
Download 20 real data center GPU images using wget for better reliability
"""

import subprocess
import os
from pathlib import Path

def download_images():
    """Download GPU data center images using wget"""

    # Create output directory
    output_dir = Path("gpu_datacenter_images")
    output_dir.mkdir(exist_ok=True)

    # Use wget to download images from a search results page
    # This approach will download real data center images
    print("Downloading GPU data center images...")

    # Create a batch script to download images
    batch_script = """
# Download 20 GPU data center images
for i in {1..20}; do
    # Different search terms to get variety of GPU data center images
    case $i in
        1|2|3|4|5) search_term="gpu+server+rack";;
        6|7|8|9|10) search_term="datacenter+gpu+cluster";;
        11|12|13|14|15) search_term="nvidia+a100+datacenter";;
        *) search_term="gpu+computing+infrastructure";;
    esac

    # Download a random image from the search results
    wget -q -O gpu_datacenter_images/gpu_datacenter_$(printf "%03d" $i).jpg \
        "https://source.unsplash.com/800x600/?$search_term" &

    # Download in batches to avoid rate limiting
    if (( i % 5 == 0 )); then
        wait
        echo "Downloaded $i images..."
    fi
done

wait
echo "Download completed!"
"""

    # Save batch script
    script_path = "download_batch.sh"
    with open(script_path, 'w') as f:
        f.write(batch_script)

    # Make script executable
    os.chmod(script_path, 0o755)

    # Execute the script
    try:
        subprocess.run(['bash', script_path], check=True)
        print("✅ Download completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during download: {e}")
    finally:
        # Clean up script
        if os.path.exists(script_path):
            os.remove(script_path)

if __name__ == "__main__":
    download_images()