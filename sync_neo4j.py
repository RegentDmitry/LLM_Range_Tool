#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sync Neo4j knowledge graph from PostgreSQL data.

This script re-creates video nodes and MENTIONS relationships in Neo4j
using data already stored in PostgreSQL. Use this after Neo4j connection
issues during batch processing.

Usage:
    python sync_neo4j.py
    python sync_neo4j.py --dry-run
    python sync_neo4j.py --video-id abc123  # sync single video
    python sync_neo4j.py --parallel 4       # use 4 parallel workers
"""

import os
import argparse
import json
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

from lib.graph_db import PokerGraphDB, VideoNode, ConceptNode
from lib.taxonomy import PokerTaxonomy

load_dotenv()


def get_db_config():
    """Get database config with Windows host detection for WSL"""
    host = os.getenv("POSTGRES_HOST")
    if not host:
        try:
            with open('/proc/net/route', 'r') as f:
                for line in f:
                    fields = line.strip().split()
                    if fields[1] == '00000000':
                        hex_ip = fields[2]
                        host = '.'.join([str(int(hex_ip[i:i+2], 16)) for i in range(6, -1, -2)])
                        break
        except:
            host = "localhost"

    return {
        "host": host,
        "port": 5432,
        "database": "rangelab",
        "user": "postgres",
        "password": "dbpass"
    }


def get_videos_from_db(conn, video_id: str = None) -> List[Dict]:
    """Get videos from PostgreSQL"""
    with conn.cursor() as cur:
        if video_id:
            cur.execute("""
                SELECT id, title, url, category
                FROM videos
                WHERE id = %s
            """, (video_id,))
        else:
            cur.execute("""
                SELECT id, title, url, category
                FROM videos
                ORDER BY id
            """)

        videos = []
        for row in cur.fetchall():
            videos.append({
                "id": row[0],
                "title": row[1],
                "url": row[2],
                "category": row[3]
            })
        return videos


def get_video_text(conn, video_id: str) -> str:
    """Get combined transcript text for a video"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT text
            FROM transcripts
            WHERE video_id = %s
            ORDER BY chunk_index
        """, (video_id,))

        texts = [row[0] for row in cur.fetchall()]
        return " ".join(texts)


def extract_concepts_for_video(
    title: str,
    text: str,
    concept_names: List[str],
    openai_client: OpenAI
) -> List[Dict]:
    """Use LLM to extract concepts from video text"""
    # Limit text to ~12000 chars
    if len(text) > 12000:
        text = text[:12000] + "..."

    prompt = f"""Analyze this poker video transcript and identify which concepts are discussed.

VIDEO TITLE: {title}

TRANSCRIPT:
{text}

KNOWN CONCEPTS (choose from these):
{', '.join(concept_names[:80])}

Rate importance of each discussed concept:
- 1.0 = Main topic
- 0.7 = Significantly discussed
- 0.4 = Mentioned
- 0.2 = Briefly referenced

Return JSON:
{{
  "concepts": [{{"name": "concept_name", "weight": 0.7}}, ...]
}}

Only include concepts actually discussed in the transcript."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a poker concept analyzer. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("concepts", [])
    except Exception as e:
        print(f"    Warning: LLM concept extraction failed: {e}")
        return []


def sync_video_to_neo4j(
    video: Dict,
    conn,
    graph_db: PokerGraphDB,
    openai_client: OpenAI,
    concept_names: List[str]
) -> Tuple[str, int, bool]:
    """Sync a single video to Neo4j. Returns (video_id, concept_count, success)"""
    video_id = video["id"]

    try:
        # Get transcript text
        text = get_video_text(conn, video_id)
        if not text:
            return (video_id, 0, False)

        # Create video node
        graph_db.create_video(VideoNode(
            id=video_id,
            title=video["title"],
            url=video["url"],
            category=video["category"]
        ))

        # Extract and link concepts
        concepts = extract_concepts_for_video(
            title=video["title"],
            text=text,
            concept_names=concept_names,
            openai_client=openai_client
        )

        for c in concepts:
            if c["name"] in concept_names:
                try:
                    graph_db.video_mentions_concept(video_id, c["name"], c["weight"])
                except:
                    pass  # Concept might not exist in graph

        return (video_id, len(concepts), True)

    except Exception as e:
        return (video_id, 0, False)


def sync_video_wrapper(args):
    """Wrapper for parallel processing"""
    video, db_config, concept_names = args

    # Each thread gets its own connections
    conn = psycopg2.connect(**db_config)
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    graph_db = PokerGraphDB()

    try:
        result = sync_video_to_neo4j(
            video=video,
            conn=conn,
            graph_db=graph_db,
            openai_client=openai_client,
            concept_names=concept_names
        )
        return result
    finally:
        conn.close()
        graph_db.close()


def sync_neo4j(
    video_id: str = None,
    dry_run: bool = False,
    parallel: int = 1
):
    """Main sync function"""

    print("=" * 60)
    print("Neo4j Sync from PostgreSQL")
    print("=" * 60)
    print(f"Dry run: {dry_run}")
    print(f"Parallel workers: {parallel}")
    if video_id:
        print(f"Single video: {video_id}")
    print()

    # Initialize services
    print("Initializing services...")

    db_config = get_db_config()
    conn = psycopg2.connect(**db_config)
    print(f"  PostgreSQL: connected ({db_config['host']})")

    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    print("  OpenAI: connected")

    graph_db = PokerGraphDB()
    if not graph_db.verify_connection():
        print("  Neo4j: FAILED TO CONNECT")
        return
    print("  Neo4j: connected")

    taxonomy = PokerTaxonomy()
    concept_names = [c.get("name") for c in taxonomy.concepts.values()]
    print(f"  Taxonomy: {len(concept_names)} concepts")
    print()

    # Get videos
    videos = get_videos_from_db(conn, video_id)
    print(f"Videos to sync: {len(videos)}")
    print()

    if dry_run:
        print("DRY RUN - Videos that would be synced:")
        for i, v in enumerate(videos[:20], 1):
            print(f"  {i}. [{v['id']}] {v['title']}")
        if len(videos) > 20:
            print(f"  ... and {len(videos) - 20} more")
        conn.close()
        graph_db.close()
        return

    # Sync videos
    synced = 0
    failed = 0
    total_concepts = 0

    if parallel > 1:
        # Parallel processing
        print(f"Syncing with {parallel} parallel workers...")

        # Prepare args for each video
        args_list = [(v, db_config, concept_names) for v in videos]

        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = {executor.submit(sync_video_wrapper, args): args[0] for args in args_list}

            pbar = tqdm(as_completed(futures), total=len(videos), desc="Syncing", unit="video")
            for future in pbar:
                video = futures[future]
                try:
                    vid_id, concept_count, success = future.result()
                    if success:
                        synced += 1
                        total_concepts += concept_count
                        pbar.set_postfix(synced=synced, concepts=total_concepts)
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    tqdm.write(f"  Error [{video['title'][:30]}]: {e}")
    else:
        # Sequential processing
        pbar = tqdm(videos, desc="Syncing", unit="video")

        for video in pbar:
            pbar.set_description(f"Syncing: {video['title'][:40]}...")

            vid_id, concept_count, success = sync_video_to_neo4j(
                video=video,
                conn=conn,
                graph_db=graph_db,
                openai_client=openai_client,
                concept_names=concept_names
            )

            if success:
                synced += 1
                total_concepts += concept_count
                pbar.set_postfix(synced=synced, concepts=total_concepts)
            else:
                failed += 1

    # Summary
    print("\n" + "=" * 60)
    print("Sync Complete!")
    print("=" * 60)
    print(f"Synced:        {synced}")
    print(f"Failed:        {failed}")
    print(f"Total MENTIONS: {total_concepts}")
    print()

    # Neo4j stats
    stats = graph_db.get_stats()
    print(f"Neo4j - Videos: {stats['videos']}, Concepts: {stats['concepts']}, Mentions: {stats['mentions']}")

    conn.close()
    graph_db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Neo4j from PostgreSQL")
    parser.add_argument("--video-id", help="Sync single video by ID")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be synced")
    parser.add_argument("--parallel", type=int, default=1,
                        help="Number of parallel workers (default: 1)")

    args = parser.parse_args()

    sync_neo4j(
        video_id=args.video_id,
        dry_run=args.dry_run,
        parallel=args.parallel
    )
