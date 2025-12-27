#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Create embeddings for video transcripts
Uses OpenAI text-embedding-3-small and stores in PostgreSQL with pgvector
"""

import os
import argparse
from typing import List, Tuple

import psycopg2
from openai import OpenAI
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()


# ============================================================================
# Configuration
# ============================================================================

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
BATCH_SIZE = 100  # OpenAI allows up to 2048 inputs per request


# ============================================================================
# Database Functions
# ============================================================================

def get_db_connection():
    """Get PostgreSQL connection"""
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="rangelab",
        user="postgres",
        password="dbpass"
    )


def get_transcripts_without_embeddings(conn) -> List[Tuple[int, str]]:
    """Get transcripts that don't have embeddings yet"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, text
            FROM transcripts
            WHERE embedding IS NULL
            ORDER BY id
        """)
        return cur.fetchall()


def update_embeddings(conn, updates: List[Tuple[List[float], int]]):
    """Update embeddings in database"""
    with conn.cursor() as cur:
        for embedding, transcript_id in updates:
            cur.execute(
                "UPDATE transcripts SET embedding = %s WHERE id = %s",
                (embedding, transcript_id)
            )
    conn.commit()


# ============================================================================
# Embedding Functions
# ============================================================================

def create_embeddings_batch(
    client: OpenAI,
    texts: List[str]
) -> List[List[float]]:
    """Create embeddings for a batch of texts"""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts
    )
    return [item.embedding for item in response.data]


def process_transcripts(
    conn,
    client: OpenAI,
    transcripts: List[Tuple[int, str]],
    batch_size: int = BATCH_SIZE
) -> int:
    """Process all transcripts and create embeddings"""

    total = len(transcripts)
    processed = 0

    # Process in batches
    for i in tqdm(range(0, total, batch_size), desc="Creating embeddings", unit="batch"):
        batch = transcripts[i:i + batch_size]

        # Extract IDs and texts
        ids = [t[0] for t in batch]
        texts = [t[1] for t in batch]

        # Create embeddings
        embeddings = create_embeddings_batch(client, texts)

        # Prepare updates
        updates = list(zip(embeddings, ids))

        # Update database
        update_embeddings(conn, updates)

        processed += len(batch)

    return processed


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Create embeddings for transcripts")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset all embeddings before creating new ones"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("Embedding Generator (pgvector)")
    print("=" * 50)

    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in .env")
        return

    print(f"Model: {EMBEDDING_MODEL}")
    print(f"Dimensions: {EMBEDDING_DIMENSIONS}")

    # Initialize OpenAI
    client = OpenAI(api_key=api_key)

    # Connect to database
    conn = get_db_connection()

    # Reset if requested
    if args.reset:
        print("Resetting all embeddings...")
        with conn.cursor() as cur:
            cur.execute("UPDATE transcripts SET embedding = NULL")
        conn.commit()

    # Get transcripts without embeddings
    print("\nChecking transcripts...")
    transcripts = get_transcripts_without_embeddings(conn)

    if not transcripts:
        print("All transcripts already have embeddings!")

        # Show stats
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM transcripts WHERE embedding IS NOT NULL")
            count = cur.fetchone()[0]
        print(f"Total embeddings: {count}")
        conn.close()
        return

    print(f"Transcripts to process: {len(transcripts)}")

    # Estimate cost
    # text-embedding-3-small: $0.02 per 1M tokens
    avg_tokens = 200
    total_tokens = len(transcripts) * avg_tokens
    cost = (total_tokens / 1_000_000) * 0.02
    print(f"Estimated cost: ${cost:.4f} ({total_tokens:,} tokens)")

    # Process
    print("\nProcessing...")
    processed = process_transcripts(conn, client, transcripts)

    # Summary
    print("\n" + "=" * 50)
    print("Embedding Complete")
    print("=" * 50)
    print(f"Processed: {processed} chunks")

    # Test search
    print("\nTest search: '3-betting strategy'")
    test_query = "3-betting strategy preflop"

    # Create query embedding
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=test_query
    )
    query_embedding = response.data[0].embedding

    # Search
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                t.text,
                v.title,
                t.timestamp,
                GREATEST(0, LEAST(1, 1 - (t.embedding <=> %s::vector))) as similarity
            FROM transcripts t
            JOIN videos v ON t.video_id = v.id
            WHERE t.embedding IS NOT NULL
            ORDER BY t.embedding <=> %s::vector
            LIMIT 3
        """, (query_embedding, query_embedding))

        results = cur.fetchall()

    print("Top 3 results:")
    for i, (text, title, timestamp, sim) in enumerate(results):
        print(f"\n  [{i+1}] {title} @ {timestamp} (similarity: {sim:.2%})")
        print(f"      {text[:100]}...")

    conn.close()


if __name__ == "__main__":
    main()
