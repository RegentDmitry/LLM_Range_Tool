#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Batch process new videos from a folder.

Workflow:
1. Scan folder for MP3 files + metadata TXT files
2. Transcribe each video with AssemblyAI
3. Create embeddings and save to PostgreSQL
4. Update Neo4j knowledge graph

Usage:
    python batch_process_videos.py --folder "/mnt/c/JN/video/postflop plo4"
    python batch_process_videos.py --folder "/mnt/c/JN/video/postflop plo4" --dry-run
    python batch_process_videos.py --folder "/mnt/c/JN/video/postflop plo4" --skip-existing
"""

import os
import argparse
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

from lib.video_processor_assemblyai import VideoProcessorAssemblyAI
from lib.graph_db import PokerGraphDB, VideoNode
from lib.taxonomy import PokerTaxonomy

load_dotenv()


# Database config
def get_db_config():
    """Get database config with Windows host detection for WSL"""
    host = os.getenv("POSTGRES_HOST")
    if not host:
        # Try to detect Windows host from WSL
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


def parse_metadata_file(txt_path: Path) -> Dict[str, str]:
    """Parse metadata from TXT file (author, url, category)"""
    metadata = {}
    if txt_path.exists():
        with open(txt_path, 'r', encoding='utf-8') as f:
            for line in f:
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip().lower()] = value.strip()
    return metadata


def generate_video_id(title: str, url: str) -> str:
    """Generate unique video ID from title and URL"""
    content = f"{title}_{url}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def get_existing_video_ids(conn) -> set:
    """Get set of existing video IDs from database"""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM videos")
        return {row[0] for row in cur.fetchall()}


def create_embeddings_batch(texts: List[str], openai_client: OpenAI, batch_size: int = 100) -> List[List[float]]:
    """Create embeddings for multiple texts in batches (parallel API calls)"""
    all_embeddings = []

    # Process in batches
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=batch
        )
        all_embeddings.extend([e.embedding for e in response.data])

    return all_embeddings


def save_video_to_db(
    conn,
    video_id: str,
    title: str,
    url: str,
    category: str,
    chunks: List,
    openai_client: OpenAI
):
    """Save video and chunks to PostgreSQL with batch embeddings"""
    with conn.cursor() as cur:
        # Insert video
        cur.execute("""
            INSERT INTO videos (id, title, url, category)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                url = EXCLUDED.url,
                category = EXCLUDED.category
        """, (video_id, title, url, category))

        # Create embeddings in batch (much faster than one-by-one)
        texts = [chunk.text for chunk in chunks]
        embeddings = create_embeddings_batch(texts, openai_client)

        # Insert chunks with embeddings
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            cur.execute("""
                INSERT INTO transcripts (video_id, chunk_index, text, start_time, end_time, timestamp, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
            """, (
                video_id,
                idx,
                chunk.text,
                chunk.start_time,
                chunk.end_time,
                chunk.timestamp,
                embedding
            ))

        conn.commit()


def extract_concepts_for_video(
    title: str,
    chunks: List,
    concept_names: List[str],
    openai_client: OpenAI
) -> Tuple[List[Dict], List[Dict]]:
    """Use LLM to extract concepts from video.

    Returns:
        Tuple of (known_concepts, new_concepts)
        - known_concepts: [{name, weight}, ...] - concepts from taxonomy
        - new_concepts: [{name, aliases, category, related}, ...] - NEW concepts to add
    """
    # Combine chunk texts (limit to ~12000 chars)
    full_text = " ".join([c.text for c in chunks])
    if len(full_text) > 12000:
        full_text = full_text[:12000] + "..."

    prompt = f"""Analyze this poker video transcript. Do TWO things:

1. Identify which KNOWN concepts are discussed (from the list below)
2. Identify any NEW poker concepts that should be added to our taxonomy

VIDEO TITLE: {title}

TRANSCRIPT:
{full_text}

KNOWN CONCEPTS (choose from these if discussed):
{', '.join(concept_names[:80])}

For KNOWN concepts, rate importance:
- 1.0 = Main topic
- 0.7 = Significantly discussed
- 0.4 = Mentioned
- 0.2 = Briefly referenced

For NEW concepts (poker strategies/terms NOT in the list above that are significantly discussed):
- Provide English name
- Provide aliases (English variations + Russian translations if possible)
- Category: preflop_action, postflop_action, position, hands, betting, strategy, game_theory, opponent_modeling
- Related concepts from known list

Return JSON:
{{
  "known_concepts": [{{"name": "concept_name", "weight": 0.7}}, ...],
  "new_concepts": [
    {{
      "name": "New Concept Name",
      "aliases": ["alias1", "alias2", "русский алиас"],
      "category": "category_name",
      "related": ["related concept 1", "related concept 2"]
    }}, ...
  ]
}}

Only include concepts actually discussed. For new_concepts, only add truly distinct poker concepts, not just video-specific terms."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a poker concept analyzer. Return only valid JSON. Be conservative about adding new concepts - only add if they represent distinct poker strategy concepts."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        result = json.loads(response.choices[0].message.content)
        return (
            result.get("known_concepts", []),
            result.get("new_concepts", [])
        )
    except Exception as e:
        print(f"    Warning: LLM concept extraction failed: {e}")
        return [], []


def add_concept_to_taxonomy(concept: Dict, taxonomy_path: str = "data/poker_taxonomy.yaml"):
    """Add a new concept to poker_taxonomy.yaml"""
    import yaml

    with open(taxonomy_path, 'r', encoding='utf-8') as f:
        taxonomy = yaml.safe_load(f)

    # Generate key from name (lowercase, underscores)
    key = concept["name"].lower().replace(" ", "_").replace("-", "_")

    # Check if already exists
    if key in taxonomy.get("concepts", {}):
        return False

    # Add new concept
    taxonomy["concepts"][key] = {
        "name": concept["name"],
        "aliases": concept.get("aliases", []),
        "related": concept.get("related", []),
        "category": concept.get("category", "strategy")
    }

    # Save back
    with open(taxonomy_path, 'w', encoding='utf-8') as f:
        yaml.dump(taxonomy, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return True


def sync_concept_to_neo4j(concept: Dict, graph_db):
    """Add new concept to Neo4j and create RELATES_TO links"""
    from lib.graph_db import ConceptNode

    try:
        # Create concept node
        graph_db.create_concept(ConceptNode(
            name=concept["name"],
            category=concept.get("category", "strategy")
        ))

        # Create RELATES_TO relationships
        for related in concept.get("related", []):
            try:
                graph_db.concept_relates_to(concept["name"], related)
            except:
                pass  # Related concept might not exist

        return True
    except Exception as e:
        print(f"      Warning: Failed to sync concept to Neo4j: {e}")
        return False


def scan_folder(folder_path: str) -> List[Dict]:
    """Scan folder for MP3 files with metadata"""
    folder = Path(folder_path)
    videos = []

    for mp3_path in sorted(folder.glob("*.mp3")):
        txt_path = mp3_path.with_suffix(".txt")
        metadata = parse_metadata_file(txt_path)

        # Extract title from filename (remove .mp3)
        title = mp3_path.stem

        # Clean up title (remove "PLO Mastermind" suffix if present)
        if title.endswith(" PLO Mastermind"):
            title = title[:-15].strip()
        elif title.endswith(" PLO Mas"):
            title = title[:-8].strip()

        videos.append({
            "mp3_path": str(mp3_path),
            "title": title,
            "url": metadata.get("url", ""),
            "category": metadata.get("category", "unknown"),
            "author": metadata.get("author", "")
        })

    return videos


def batch_process(
    folder_path: str,
    dry_run: bool = False,
    skip_existing: bool = True,
    limit: int = 0
):
    """Main batch processing function"""

    print("=" * 60)
    print("Batch Video Processor")
    print("=" * 60)
    print(f"Folder: {folder_path}")
    print(f"Dry run: {dry_run}")
    print(f"Skip existing: {skip_existing}")
    print()

    # Scan folder
    print("Scanning folder...")
    videos = scan_folder(folder_path)
    print(f"Found {len(videos)} MP3 files")
    print()

    if not videos:
        print("No videos found!")
        return

    if dry_run:
        print("DRY RUN - Videos that would be processed:")
        for i, v in enumerate(videos[:20], 1):
            print(f"  {i}. {v['title']}")
            print(f"     URL: {v['url']}")
            print(f"     Category: {v['category']}")
        if len(videos) > 20:
            print(f"  ... and {len(videos) - 20} more")
        return

    # Initialize services
    print("Initializing services...")

    db_config = get_db_config()
    conn = psycopg2.connect(**db_config)
    print(f"  PostgreSQL: connected ({db_config['host']})")

    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    print("  OpenAI: connected")

    processor = VideoProcessorAssemblyAI()
    print("  AssemblyAI: connected")

    graph_db = None
    try:
        graph_db = PokerGraphDB()
        if graph_db.verify_connection():
            print("  Neo4j: connected")
        else:
            graph_db = None
            print("  Neo4j: not available (will skip graph updates)")
    except:
        print("  Neo4j: not available (will skip graph updates)")

    taxonomy = PokerTaxonomy()
    concept_names = [c.get("name") for c in taxonomy.concepts.values()]
    print(f"  Taxonomy: {len(concept_names)} concepts")
    print()

    # Get existing videos
    existing_ids = get_existing_video_ids(conn) if skip_existing else set()
    print(f"Existing videos in DB: {len(existing_ids)}")
    print()

    # Process videos
    processed = 0
    skipped = 0
    failed = 0
    new_concepts_added = 0

    # Apply limit if specified
    if limit > 0:
        videos = videos[:limit]

    # Main progress bar
    pbar = tqdm(videos, desc="Processing videos", unit="video")

    for video in pbar:
        title = video["title"]
        url = video["url"]
        video_id = generate_video_id(title, url)

        pbar.set_description(f"Processing: {title[:40]}...")

        # Skip if exists
        if skip_existing and video_id in existing_ids:
            pbar.set_postfix(status="skipped")
            skipped += 1
            continue

        try:
            # 1. Transcribe
            pbar.set_postfix(step="transcribing")
            transcript, chunks = processor.process_video(
                video_path=video["mp3_path"],
                video_id=video_id,
                title=title,
                url=url,
                chunk_duration=60.0,
                overlap=10.0,
                use_chapters=False
            )

            # 2. Save to PostgreSQL (with batch embeddings)
            pbar.set_postfix(step=f"embeddings ({len(chunks)} chunks)")
            save_video_to_db(
                conn=conn,
                video_id=video_id,
                title=title,
                url=url,
                category=video["category"],
                chunks=chunks,
                openai_client=openai_client
            )

            # 3. Extract concepts (known + new)
            pbar.set_postfix(step="analyzing concepts")
            known_concepts, new_concepts = extract_concepts_for_video(
                title=title,
                chunks=chunks,
                concept_names=concept_names,
                openai_client=openai_client
            )

            # 4. Handle NEW concepts (add to taxonomy + Neo4j)
            if new_concepts:
                for nc in new_concepts:
                    if add_concept_to_taxonomy(nc):
                        tqdm.write(f"  + NEW CONCEPT: {nc['name']}")
                        new_concepts_added += 1
                        concept_names.append(nc["name"])  # Update local list
                        if graph_db:
                            sync_concept_to_neo4j(nc, graph_db)

            # 5. Update Neo4j with video + MENTIONS
            if graph_db:
                pbar.set_postfix(step="updating graph")

                # Create video node
                graph_db.create_video(VideoNode(
                    id=video_id,
                    title=title,
                    url=url,
                    category=video["category"]
                ))

                # Link known concepts
                for c in known_concepts:
                    if c["name"] in concept_names:
                        graph_db.video_mentions_concept(video_id, c["name"], c["weight"])

                # Link new concepts
                for nc in new_concepts:
                    graph_db.video_mentions_concept(video_id, nc["name"], 0.7)

            processed += 1
            pbar.set_postfix(status="done", concepts=len(known_concepts) + len(new_concepts))

        except Exception as e:
            tqdm.write(f"  ✗ Error [{title[:30]}]: {e}")
            failed += 1
            continue

    pbar.close()

    # Summary
    print("\n" + "=" * 60)
    print("Batch Processing Complete!")
    print("=" * 60)
    print(f"Processed:     {processed}")
    print(f"Skipped:       {skipped}")
    print(f"Failed:        {failed}")
    print(f"New concepts:  {new_concepts_added}")
    print()

    # Final stats
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM videos")
        total_videos = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM transcripts")
        total_chunks = cur.fetchone()[0]

    print(f"Total videos in DB: {total_videos}")
    print(f"Total chunks in DB: {total_chunks}")

    if graph_db:
        stats = graph_db.get_stats()
        print(f"Neo4j - Videos: {stats['videos']}, Mentions: {stats['mentions']}")
        graph_db.close()

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch process videos from folder")
    parser.add_argument("--folder", required=True, help="Folder with MP3 and TXT files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")
    parser.add_argument("--skip-existing", action="store_true", default=True,
                       help="Skip videos already in database (default: True)")
    parser.add_argument("--no-skip", action="store_true", help="Process all videos even if exist")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of videos to process")

    args = parser.parse_args()

    skip_existing = not args.no_skip

    batch_process(
        folder_path=args.folder,
        dry_run=args.dry_run,
        skip_existing=skip_existing,
        limit=args.limit
    )
