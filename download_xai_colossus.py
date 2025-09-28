#!/usr/bin/env python3
"""
Download impressive xAI Colossus 2 datacenter images using aria2c
Focus on the most visually stunning and impactful images
"""

import subprocess
import os
from pathlib import Path

def download_xai_colossus_images():
    """Download impressive xAI Colossus 2 datacenter images"""

    # Create output directory
    output_dir = Path("xai_colossus_images")
    output_dir.mkdir(exist_ok=True)

    print("🚀 Downloading impressive xAI Colossus 2 datacenter images...")

    # High-impact search terms for xAI Colossus 2 and massive GPU clusters
    search_terms = [
        "xAI+Colossus+2+datacenter",
        "worlds+largest+GPU+cluster",
        "100000+GPU+datacenter",
        "massive+AI+infrastructure",
        "colossal+supercomputer",
        "exascale+AI+computing",
        "Musk+xAI+datacenter",
        "Memphis+supercomputer",
        "giant+GPU+farm",
        "largest+AI+cluster"
    ]

    # Create aria2c input file with multiple sources per search term
    input_file = "xai_colossus_urls.txt"
    with open(input_file, 'w') as f:
        for i, term in enumerate(search_terms, 1):
            # Create multiple URLs for each search term to increase success rate
            base_url = f"https://source.unsplash.com/1600x900/?{term}"

            # Add variations for different aspect ratios and sources
            urls = [
                f"{base_url}&sig={i}",
                f"https://source.unsplash.com/1920x1080/?{term}&sig={i+100}",
                f"https://source.unsplash.com/2560x1440/?{term}&sig={i+200}",
                f"https://images.unsplash.com/photo-1579546929662-711aa81148cf?auto=format&fit=crop&w=1600&q=80&sig={i+300}",
                f"https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1600&q=80&sig={i+400}",
            ]

            for j, url in enumerate(urls):
                filename = f"xai_colossus_{i:02d}_{j+1}.jpg"
                f.write(f"{url}\n")
                f.write(f"  out={filename}\n")

    try:
        # Run aria2c with optimized settings for high-quality downloads
        cmd = [
            'aria2c',
            '-i', input_file,
            '-d', str(output_dir),
            '-x', '16',  # Max connections per server
            '-s', '16',  # Max connections
            '-j', '20',  # Max concurrent downloads
            '--auto-file-renaming=false',
            '--continue=true',
            '--max-tries=5',
            '--timeout=60',
            '--max-file-not-found=5',
            '--file-allocation=none',
            '--allow-overwrite=true',
            '--always-resume=true',
            '--retry-wait=5',
            '--split=16',
            '--min-split-size=1M',
            '--stream-piece-selector=geom'
        ]

        print(f"📥 Starting download of high-impact xAI Colossus images...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Download completed successfully!")
        else:
            print(f"⚠️ Download completed with some errors")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error during download: {e}")
    except FileNotFoundError:
        print("❌ aria2c not found. Installing...")
        subprocess.run(['brew', 'install', 'aria2'], check=True)
        print("🔧 aria2c installed. Please run the script again.")
        return
    finally:
        # Clean up input file
        if os.path.exists(input_file):
            os.remove(input_file)

    # Verify and report downloaded images
    downloaded_files = list(output_dir.glob("*.jpg"))
    print(f"\n🎯 Verification Results:")
    print(f"📁 Total files downloaded: {len(downloaded_files)}")

    valid_images = 0
    for file in downloaded_files:
        if file.stat().st_size > 1024:  # Larger than 1KB
            valid_images += 1
            print(f"✅ {file.name} ({file.stat().st_size:,} bytes)")
        else:
            print(f"❌ {file.name} (too small: {file.stat().st_size} bytes)")

    print(f"\n🏆 Successfully downloaded {valid_images} high-quality xAI Colossus images!")
    return valid_images

if __name__ == "__main__":
    download_xai_colossus_images()