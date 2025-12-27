#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Index video metadata from txt files to JSON
Reads all .txt files from video directory and creates structured JSON
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from tqdm import tqdm


@dataclass
class VideoMetadata:
    """Video metadata structure"""
    id: str  # MD5 hash of URL
    title: str  # From filename
    author: str
    url: str
    category: str
    file_path: str  # Path to video/audio file
    file_type: str  # mp4, mp3, etc.
    file_size_mb: Optional[float]
    indexed_at: str


def parse_txt_file(txt_path: Path) -> Dict[str, str]:
    """Parse metadata from txt file"""
    metadata = {}
    with open(txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip().lower()] = value.strip()
    return metadata


def find_media_file(txt_path: Path) -> Optional[Path]:
    """Find corresponding media file (mp4 or mp3)"""
    base_name = txt_path.stem
    parent = txt_path.parent

    for ext in ['.mp4', '.mp3', '.wav', '.m4a']:
        media_path = parent / f"{base_name}{ext}"
        if media_path.exists():
            return media_path
    return None


def get_file_size_mb(file_path: Path) -> Optional[float]:
    """Get file size in MB"""
    if file_path and file_path.exists():
        return round(file_path.stat().st_size / (1024 * 1024), 2)
    return None


def generate_id(url: str) -> str:
    """Generate unique ID from URL"""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def index_videos(
    video_dir: str,
    output_file: str = "videos_index.json"
) -> List[VideoMetadata]:
    """
    Index all videos from directory

    Args:
        video_dir: Directory with video files and txt metadata
        output_file: Output JSON file path

    Returns:
        List of VideoMetadata objects
    """
    video_path = Path(video_dir)
    if not video_path.exists():
        raise ValueError(f"Directory not found: {video_dir}")

    txt_files = list(video_path.glob("*.txt"))
    print(f"\nFound {len(txt_files)} txt files in {video_dir}")

    videos = []
    errors = []
    duplicates = {}

    for txt_file in tqdm(txt_files, desc="Indexing videos", unit="file"):
        try:
            # Parse metadata
            meta = parse_txt_file(txt_file)

            if 'url' not in meta:
                errors.append(f"{txt_file.name}: Missing URL")
                continue

            url = meta['url']

            # Check for duplicate URLs
            if url in duplicates:
                errors.append(f"DUPLICATE URL: {txt_file.name} and {duplicates[url]}")
                continue
            duplicates[url] = txt_file.name

            # Find media file
            media_file = find_media_file(txt_file)

            # Create metadata
            video_meta = VideoMetadata(
                id=generate_id(url),
                title=txt_file.stem.replace(" PLO Mastermind", "").strip(),
                author=meta.get('author', 'Unknown').strip(),
                url=url,
                category=meta.get('category', 'uncategorized'),
                file_path=str(media_file) if media_file else "",
                file_type=media_file.suffix[1:] if media_file else "",
                file_size_mb=get_file_size_mb(media_file) if media_file else None,
                indexed_at=datetime.now().isoformat()
            )
            videos.append(video_meta)

        except Exception as e:
            errors.append(f"{txt_file.name}: {str(e)}")

    # Save to JSON
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(
            {
                "metadata": {
                    "total_videos": len(videos),
                    "indexed_at": datetime.now().isoformat(),
                    "source_directory": str(video_path.absolute())
                },
                "videos": [asdict(v) for v in videos]
            },
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"\n{'='*50}")
    print(f"Indexed {len(videos)} videos to {output_file}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for err in errors:
            print(f"  - {err}")

    # Stats
    authors = {}
    total_size = 0
    for v in videos:
        authors[v.author] = authors.get(v.author, 0) + 1
        if v.file_size_mb:
            total_size += v.file_size_mb

    print(f"\nStatistics:")
    print(f"  Total size: {total_size:.1f} MB")
    print(f"  Authors:")
    for author, count in sorted(authors.items(), key=lambda x: -x[1]):
        print(f"    - {author}: {count} videos")

    return videos


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Index video metadata to JSON")
    parser.add_argument(
        "--dir", "-d",
        default="C:/JN/video/preflop",
        help="Video directory path"
    )
    parser.add_argument(
        "--output", "-o",
        default="videos_index.json",
        help="Output JSON file"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("Video Indexer")
    print("=" * 50)

    index_videos(args.dir, args.output)


if __name__ == "__main__":
    main()
