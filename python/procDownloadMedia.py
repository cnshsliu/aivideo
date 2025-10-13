#!/usr/bin/env python3
import os
import shutil
import hashlib
import argparse
from datetime import datetime
import uuid

def get_all_files(source_dir):
    """Recursively get all files in the source directory."""
    files = []
    for root, dirs, filenames in os.walk(source_dir):
        for filename in filenames:
            files.append(os.path.join(root, filename))
    return files

def compute_md5(file_path):
    """Compute MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def main():
    parser = argparse.ArgumentParser(description="Process and deduplicate media files.")
    parser.add_argument("--source", required=True, help="Source directory containing files")
    parser.add_argument("--target", required=True, help="Target directory to copy unique files")
    args = parser.parse_args()

    source_dir = args.source
    target_dir = args.target

    if not os.path.exists(source_dir):
        print(f"Source directory {source_dir} does not exist.")
        return

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # Get all files
    all_files = get_all_files(source_dir)
    print(f"Found {len(all_files)} files in source directory.")

    # Compute hashes and track unique files
    hash_to_file = {}
    for file_path in all_files:
        file_hash = compute_md5(file_path)
        if file_hash not in hash_to_file:
            hash_to_file[file_hash] = file_path

    print(f"Found {len(hash_to_file)} unique files after deduplication.")

    # Copy unique files with new names
    for file_path in hash_to_file.values():
        # Get original suffix
        _, suffix = os.path.splitext(file_path)

        # Generate new name: date_timestamp_UUID
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        unique_id = str(uuid.uuid4())
        new_name = f"{timestamp}_{unique_id}{suffix}"

        target_path = os.path.join(target_dir, new_name)
        shutil.copy2(file_path, target_path)
        print(f"Copied {file_path} to {target_path}")

    print("Processing complete.")

if __name__ == "__main__":
    main()
