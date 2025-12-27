#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Transcribe videos using AssemblyAI
Uploads videos, gets transcriptions with timestamps, saves to PostgreSQL
"""

import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import assemblyai as aai
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class Config:
    """Configuration"""
    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "rangelab"
    db_user: str = "postgres"
    db_password: str = "dbpass"

    # AssemblyAI
    assemblyai_key: str = ""

    # Chunking
    chunk_duration_sec: int = 60  # 1 minute chunks

    # Processing
    max_concurrent: int = 5  # AssemblyAI allows 5 concurrent


# ============================================================================
# Database Functions
# ============================================================================

def get_db_connection(config: Config):
    """Get database connection"""
    return psycopg2.connect(
        host=config.db_host,
        port=config.db_port,
        database=config.db_name,
        user=config.db_user,
        password=config.db_password
    )


def get_videos_to_transcribe(conn, limit: Optional[int] = None) -> List[Dict]:
    """Get videos that haven't been transcribed yet"""
    with conn.cursor() as cur:
        sql = """
            SELECT v.id, v.title, v.file_path, v.file_type
            FROM videos v
            LEFT JOIN transcripts t ON v.id = t.video_id
            WHERE t.id IS NULL
            AND v.file_path IS NOT NULL
            AND v.file_path != ''
            ORDER BY v.title
        """
        if limit:
            sql += f" LIMIT {limit}"

        cur.execute(sql)
        columns = ['id', 'title', 'file_path', 'file_type']
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def save_transcript_chunks(conn, video_id: str, chunks: List[Dict]):
    """Save transcript chunks to database"""
    if not chunks:
        return 0

    values = [
        (
            video_id,
            chunk['chunk_index'],
            chunk['text'],
            chunk['start_time'],
            chunk['end_time'],
            chunk['timestamp']
        )
        for chunk in chunks
    ]

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO transcripts (video_id, chunk_index, text, start_time, end_time, timestamp)
            VALUES %s
            ON CONFLICT (video_id, chunk_index) DO UPDATE SET
                text = EXCLUDED.text,
                start_time = EXCLUDED.start_time,
                end_time = EXCLUDED.end_time,
                timestamp = EXCLUDED.timestamp
            """,
            values,
            template="(%s, %s, %s, %s, %s, %s)"
        )
        conn.commit()

    return len(values)


# ============================================================================
# AssemblyAI Functions
# ============================================================================

def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS format"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def transcribe_file(file_path: str, config: Config) -> Optional[aai.Transcript]:
    """Transcribe a single file using AssemblyAI"""
    try:
        transcriber = aai.Transcriber()

        # Configure transcription
        aai_config = aai.TranscriptionConfig(
            language_detection=True,  # Auto-detect language
            punctuate=True,
            format_text=True,
        )

        # Submit for transcription
        transcript = transcriber.transcribe(file_path, config=aai_config)

        if transcript.status == aai.TranscriptStatus.error:
            print(f"    Error: {transcript.error}")
            return None

        return transcript

    except Exception as e:
        print(f"    Exception: {e}")
        return None


def create_chunks(transcript: aai.Transcript, chunk_duration_sec: int = 60) -> List[Dict]:
    """Split transcript into time-based chunks"""
    if not transcript.words:
        # No word-level timestamps, use full text
        return [{
            'chunk_index': 0,
            'text': transcript.text or "",
            'start_time': 0.0,
            'end_time': 0.0,
            'timestamp': "0:00"
        }]

    chunks = []
    current_chunk = {
        'words': [],
        'start_ms': None,
        'end_ms': None
    }
    chunk_duration_ms = chunk_duration_sec * 1000

    for word in transcript.words:
        if current_chunk['start_ms'] is None:
            current_chunk['start_ms'] = word.start

        current_chunk['words'].append(word.text)
        current_chunk['end_ms'] = word.end

        # Check if chunk is complete
        if (word.end - current_chunk['start_ms']) >= chunk_duration_ms:
            # Save chunk
            start_sec = current_chunk['start_ms'] / 1000.0
            end_sec = current_chunk['end_ms'] / 1000.0

            chunks.append({
                'chunk_index': len(chunks),
                'text': ' '.join(current_chunk['words']),
                'start_time': start_sec,
                'end_time': end_sec,
                'timestamp': format_timestamp(start_sec)
            })

            # Reset
            current_chunk = {
                'words': [],
                'start_ms': None,
                'end_ms': None
            }

    # Don't forget the last chunk
    if current_chunk['words']:
        start_sec = current_chunk['start_ms'] / 1000.0
        end_sec = current_chunk['end_ms'] / 1000.0

        chunks.append({
            'chunk_index': len(chunks),
            'text': ' '.join(current_chunk['words']),
            'start_time': start_sec,
            'end_time': end_sec,
            'timestamp': format_timestamp(start_sec)
        })

    return chunks


# ============================================================================
# Main Processing
# ============================================================================

def process_videos(config: Config, limit: Optional[int] = None, dry_run: bool = False):
    """Process all videos that need transcription"""

    # Setup AssemblyAI
    aai.settings.api_key = config.assemblyai_key

    # Get videos to process
    conn = get_db_connection(config)
    videos = get_videos_to_transcribe(conn, limit)

    if not videos:
        print("No videos to transcribe.")
        return

    print(f"\nVideos to transcribe: {len(videos)}")

    if dry_run:
        print("\n[DRY RUN] Would transcribe:")
        for v in videos:
            print(f"  - {v['title']} ({v['file_type']})")
        return

    # Estimate cost
    # AssemblyAI: $0.25 per hour
    # Rough estimate: 40 videos * 20 min avg = 13.3 hours * $0.25 = ~$3.33
    print(f"\nEstimated cost: ~${len(videos) * 0.08:.2f} (assuming 20 min avg)")
    print()

    total_chunks = 0
    errors = []

    for video in tqdm(videos, desc="Transcribing", unit="video"):
        video_id = video['id']
        title = video['title']
        file_path = video['file_path']

        tqdm.write(f"\n  Processing: {title}")

        # Check file exists
        if not Path(file_path).exists():
            tqdm.write(f"    File not found: {file_path}")
            errors.append(f"{title}: File not found")
            continue

        # Transcribe
        tqdm.write(f"    Uploading to AssemblyAI...")
        transcript = transcribe_file(file_path, config)

        if not transcript:
            errors.append(f"{title}: Transcription failed")
            continue

        # Create chunks
        chunks = create_chunks(transcript, config.chunk_duration_sec)
        tqdm.write(f"    Created {len(chunks)} chunks")

        # Save to database
        saved = save_transcript_chunks(conn, video_id, chunks)
        total_chunks += saved
        tqdm.write(f"    Saved {saved} chunks to database")

    conn.close()

    # Summary
    print("\n" + "=" * 50)
    print("Transcription Complete")
    print("=" * 50)
    print(f"  Videos processed: {len(videos) - len(errors)}")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Errors: {len(errors)}")

    if errors:
        print("\nErrors:")
        for err in errors:
            print(f"  - {err}")


def main():
    parser = argparse.ArgumentParser(description="Transcribe videos with AssemblyAI")
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="Limit number of videos to process"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be transcribed without doing it"
    )
    parser.add_argument(
        "--chunk-duration",
        type=int,
        default=60,
        help="Chunk duration in seconds (default: 60)"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("Video Transcription (AssemblyAI)")
    print("=" * 50)

    # Load config
    config = Config(
        assemblyai_key=os.getenv('ASSEMBLYAI_API_KEY', ''),
        chunk_duration_sec=args.chunk_duration
    )

    if not config.assemblyai_key:
        print("Error: ASSEMBLYAI_API_KEY not found in .env")
        return

    print(f"API Key: {config.assemblyai_key[:8]}...")
    print(f"Chunk duration: {config.chunk_duration_sec} seconds")

    process_videos(config, limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
