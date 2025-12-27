#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Upload indexed video metadata to PostgreSQL
Creates tables and loads data from JSON index
"""

import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from tqdm import tqdm

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()


# ============================================================================
# Database Configuration
# ============================================================================

@dataclass
class DBConfig:
    """PostgreSQL connection config"""
    host: str = "localhost"
    port: int = 5432
    database: str = "rangelab"
    user: str = "postgres"
    password: str = "dbpass"


# ============================================================================
# SQL Schemas
# ============================================================================

CREATE_EXTENSION_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;
"""

CREATE_VIDEOS_TABLE = """
CREATE TABLE IF NOT EXISTS videos (
    id VARCHAR(12) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    author VARCHAR(100),
    url TEXT UNIQUE NOT NULL,
    category VARCHAR(100),
    file_path TEXT,
    file_type VARCHAR(10),
    file_size_mb FLOAT,
    indexed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_TRANSCRIPTS_TABLE = """
CREATE TABLE IF NOT EXISTS transcripts (
    id SERIAL PRIMARY KEY,
    video_id VARCHAR(12) REFERENCES videos(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    start_time FLOAT,
    end_time FLOAT,
    timestamp VARCHAR(20),
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(video_id, chunk_index)
);
"""

CREATE_TRANSCRIPTS_TABLE_BASIC = """
CREATE TABLE IF NOT EXISTS transcripts (
    id SERIAL PRIMARY KEY,
    video_id VARCHAR(12) REFERENCES videos(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    start_time FLOAT,
    end_time FLOAT,
    timestamp VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(video_id, chunk_index)
);
"""

CREATE_EMBEDDING_INDEX = """
CREATE INDEX IF NOT EXISTS idx_transcripts_embedding
ON transcripts USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
"""

INSERT_VIDEO_SQL = """
INSERT INTO videos (id, title, author, url, category, file_path, file_type, file_size_mb, indexed_at)
VALUES %s
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    author = EXCLUDED.author,
    category = EXCLUDED.category,
    file_path = EXCLUDED.file_path,
    file_type = EXCLUDED.file_type,
    file_size_mb = EXCLUDED.file_size_mb,
    indexed_at = EXCLUDED.indexed_at;
"""


# ============================================================================
# Database Functions
# ============================================================================

def get_connection(config: DBConfig) -> psycopg2.extensions.connection:
    """Create database connection"""
    return psycopg2.connect(
        host=config.host,
        port=config.port,
        database=config.database,
        user=config.user,
        password=config.password
    )


def create_database_if_not_exists(config: DBConfig):
    """Create database if it doesn't exist"""
    # Connect to default postgres database
    temp_config = DBConfig(
        host=config.host,
        port=config.port,
        database="postgres",
        user=config.user,
        password=config.password
    )

    conn = get_connection(temp_config)
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            # Check if database exists
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (config.database,)
            )
            if not cur.fetchone():
                print(f"Creating database: {config.database}")
                cur.execute(f'CREATE DATABASE {config.database}')
            else:
                print(f"Database exists: {config.database}")
    finally:
        conn.close()


def setup_schema(conn: psycopg2.extensions.connection, skip_pgvector: bool = True):
    """Create tables and indexes"""
    with conn.cursor() as cur:
        print("Setting up database schema...")

        # Create pgvector extension (optional - install later)
        if not skip_pgvector:
            try:
                print("  - Creating pgvector extension")
                cur.execute(CREATE_EXTENSION_SQL)
            except Exception as e:
                print(f"  - pgvector not available: {e}")
                print("  - Continuing without vector support...")
                conn.rollback()

        # Create videos table
        print("  - Creating videos table")
        cur.execute(CREATE_VIDEOS_TABLE)

        # Create transcripts table (without vector column for now)
        print("  - Creating transcripts table")
        cur.execute(CREATE_TRANSCRIPTS_TABLE_BASIC)

        conn.commit()
        print("Schema created successfully")


def load_videos_from_json(json_path: str) -> List[Dict[str, Any]]:
    """Load videos from JSON index file"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('videos', [])


def upload_videos(
    conn: psycopg2.extensions.connection,
    videos: List[Dict[str, Any]]
) -> int:
    """Upload videos to database"""
    if not videos:
        print("No videos to upload")
        return 0

    # Prepare data for insertion
    values = []
    for video in tqdm(videos, desc="Preparing video data", unit="video"):
        indexed_at = None
        if video.get('indexed_at'):
            try:
                indexed_at = datetime.fromisoformat(video['indexed_at'])
            except (ValueError, TypeError):
                indexed_at = datetime.now()

        values.append((
            video['id'],
            video['title'],
            video.get('author', 'Unknown'),
            video['url'],
            video.get('category', 'uncategorized'),
            video.get('file_path', ''),
            video.get('file_type', ''),
            video.get('file_size_mb'),
            indexed_at
        ))

    # Insert data
    with conn.cursor() as cur:
        print(f"\nUploading {len(values)} videos to database...")
        execute_values(
            cur,
            INSERT_VIDEO_SQL,
            values,
            template="(%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        conn.commit()

    return len(values)


def get_stats(conn: psycopg2.extensions.connection) -> Dict[str, Any]:
    """Get database statistics"""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM videos")
        video_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM transcripts")
        transcript_count = cur.fetchone()[0]

        cur.execute("""
            SELECT author, COUNT(*) as cnt
            FROM videos
            GROUP BY author
            ORDER BY cnt DESC
        """)
        authors = cur.fetchall()

        cur.execute("SELECT SUM(file_size_mb) FROM videos")
        total_size = cur.fetchone()[0] or 0

    return {
        "videos": video_count,
        "transcripts": transcript_count,
        "total_size_mb": round(total_size, 2),
        "authors": dict(authors)
    }


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Upload videos to PostgreSQL")
    parser.add_argument(
        "--json", "-j",
        default="videos_index.json",
        help="JSON index file"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="PostgreSQL host"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5432,
        help="PostgreSQL port"
    )
    parser.add_argument(
        "--database", "-d",
        default="rangelab",
        help="Database name"
    )
    parser.add_argument(
        "--user", "-u",
        default="postgres",
        help="Database user"
    )
    parser.add_argument(
        "--password", "-p",
        default="dbpass",
        help="Database password"
    )
    parser.add_argument(
        "--setup-only",
        action="store_true",
        help="Only create schema, don't upload data"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("PostgreSQL Video Uploader")
    print("=" * 50)

    config = DBConfig(
        host=args.host,
        port=args.port,
        database=args.database,
        user=args.user,
        password=args.password
    )

    print(f"\nDatabase: {config.user}@{config.host}:{config.port}/{config.database}")

    # Create database if needed
    create_database_if_not_exists(config)

    # Connect to target database
    conn = get_connection(config)

    try:
        # Setup schema
        setup_schema(conn)

        if args.setup_only:
            print("\nSchema setup complete (--setup-only mode)")
            return

        # Load and upload videos
        json_path = Path(args.json)
        if not json_path.exists():
            print(f"\nJSON file not found: {json_path}")
            print("Run 'python index_videos.py' first to create the index")
            return

        videos = load_videos_from_json(str(json_path))
        uploaded = upload_videos(conn, videos)

        # Show stats
        print("\n" + "=" * 50)
        print("Database Statistics")
        print("=" * 50)
        stats = get_stats(conn)
        print(f"  Videos: {stats['videos']}")
        print(f"  Transcripts: {stats['transcripts']}")
        print(f"  Total size: {stats['total_size_mb']} MB")
        print(f"  Authors:")
        for author, count in stats['authors'].items():
            print(f"    - {author}: {count} videos")

        print("\nUpload complete!")

    except psycopg2.Error as e:
        print(f"\nDatabase error: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
