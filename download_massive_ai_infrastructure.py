#!/usr/bin/env python3
"""
Download massive, impressive AI infrastructure and supercomputer images
Focus on the most visually stunning datacenter photos available
"""

import subprocess
import os
from pathlib import Path

def download_massive_ai_infrastructure():
    """Download the most impressive AI infrastructure images"""

    # Create output directory
    output_dir = Path("xai_colossus_images")
    output_dir.mkdir(exist_ok=True)

    print("🌟 Downloading the most impressive AI infrastructure images...")

    # High-impact search terms for massive datacenters and supercomputers
    search_terms = [
        "supercomputer+datacenter+hall",
        "massive+server+room",
        "exascale+computing+center",
        "largest+datacenter+world",
        "AI+training+cluster",
        "GPU+supercomputer",
        "hyperscale+datacenter",
        "quantum+computing+center",
        "exascale+supercomputer",
        "massive+computing+infrastructure",
        "world+largest+computer",
        "AI+factory+datacenter",
        "colossal+server+farm",
        "datacenter+cathedral",
        "computing+cathedral",
        "tech+cathedral"
    ]

    # Create aria2c input file with high-resolution sources
    input_file = "massive_ai_urls.txt"
    with open(input_file, 'w') as f:
        for i, term in enumerate(search_terms, 21):  # Start from 21 to avoid conflicts
            # Multiple high-resolution sources for each search term
            urls = [
                f"https://source.unsplash.com/3840x2160/?{term}&sig={i}",
                f"https://source.unsplash.com/2560x1440/?{term}&sig={i+100}",
                f"https://source.unsplash.com/1920x1080/?{term}&sig={i+200}",
                f"https://source.unsplash.com/1600x900/?{term}&sig={i+300}",
                f"https://source.unsplash.com/1280x720/?{term}&sig={i+400}",
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
            '-j', '25',  # Max concurrent downloads
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
            '--stream-piece-selector=geom',
            '--enable-rpc=false',
            '--enable-http-pipelining=true',
            '--max-connection-per-server=16'
        ]

        print(f"📥 Starting download of {len(search_terms)*5} massive AI infrastructure images...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Download completed successfully!")
        else:
            print(f"⚠️ Download completed with some errors")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error during download: {e}")
    finally:
        # Clean up input file
        if os.path.exists(input_file):
            os.remove(input_file)

    # Verify and report downloaded images
    downloaded_files = list(output_dir.glob("xai_colossus_*.jpg"))
    print(f"\n🎯 Verification Results:")
    print(f"📁 Total files downloaded: {len(downloaded_files)}")

    valid_images = 0
    total_size = 0
    for file in sorted(downloaded_files):
        if file.stat().st_size > 1024:  # Larger than 1KB
            valid_images += 1
            total_size += file.stat().st_size
            size_mb = file.stat().st_size / 1024 / 1024
            print(f"✅ {file.name} ({size_mb:.1f} MB)")

    print(f"\n🏆 Successfully downloaded {valid_images} high-quality images!")
    print(f"💾 Total size: {total_size/1024/1024:.1f} MB")
    return valid_images

if __name__ == "__main__":
    download_massive_ai_infrastructure()