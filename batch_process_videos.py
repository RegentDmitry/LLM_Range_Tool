#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Batch process new videos from a folder.

Workflow:
1. Scan folder for MP3 files + metadata TXT files
2. Transcribe each video with AssemblyAI (parallel)
3. Create embeddings and save to PostgreSQL
4. Update Neo4j knowledge graph

Usage:
    python batch_process_videos.py --folder "/mnt/c/JN/video/postflop plo4"
    python batch_process_videos.py --folder "/mnt/c/JN/video/postflop plo4" --dry-run
    python batch_process_videos.py --folder "/mnt/c/JN/video/postflop plo4" --parallel 4
"""

import os
import argparse
import hashlib
import json
import threading
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

# Thread-safe lock for taxonomy updates
taxonomy_lock = threading.Lock()


# Database config
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
    """Create embeddings for multiple texts in batches"""
    all_embeddings = []
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
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO videos (id, title, url, category)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    url = EXCLUDED.url,
                    category = EXCLUDED.category
            """, (video_id, title, url, category))

            if chunks:
                texts = [chunk.text for chunk in chunks]
                embeddings = create_embeddings_batch(texts, openai_client)

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
    except Exception as e:
        conn.rollback()
        raise e


def extract_concepts_for_video(
    title: str,
    chunks: List,
    concept_names: List[str],
    openai_client: OpenAI
) -> Tuple[List[Dict], List[Dict]]:
    """Use LLM to extract concepts from video."""
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

Only include concepts actually discussed. For new_concepts, only add truly distinct poker concepts."""

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
        return (
            result.get("known_concepts", []),
            result.get("new_concepts", [])
        )
    except Exception as e:
        return [], []


def add_concept_to_taxonomy(concept: Dict, taxonomy_path: str = "data/poker_taxonomy.yaml"):
    """Add a new concept to poker_taxonomy.yaml (thread-safe)"""
    import yaml

    with taxonomy_lock:
        with open(taxonomy_path, 'r', encoding='utf-8') as f:
            taxonomy = yaml.safe_load(f)

        key = concept["name"].lower().replace(" ", "_").replace("-", "_")

        if key in taxonomy.get("concepts", {}):
            return False

        taxonomy["concepts"][key] = {
            "name": concept["name"],
            "aliases": concept.get("aliases", []),
            "related": concept.get("related", []),
            "category": concept.get("category", "strategy")
        }

        with open(taxonomy_path, 'w', encoding='utf-8') as f:
            yaml.dump(taxonomy, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return True


def sync_concept_to_neo4j(concept: Dict, graph_db):
    """Add new concept to Neo4j and create RELATES_TO links"""
    from lib.graph_db import ConceptNode

    try:
        graph_db.create_concept(ConceptNode(
            name=concept["name"],
            category=concept.get("category", "strategy")
        ))

        for related in concept.get("related", []):
            try:
                graph_db.concept_relates_to(concept["name"], related)
            except:
                pass

        return True
    except Exception as e:
        return False


def scan_folder(folder_path: str) -> List[Dict]:
    """Scan folder for MP3 files with metadata"""
    folder = Path(folder_path)
    videos = []

    for mp3_path in sorted(folder.glob("*.mp3")):
        txt_path = mp3_path.with_suffix(".txt")
        metadata = parse_metadata_file(txt_path)

        title = mp3_path.stem
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


def process_single_video(
    video: Dict,
    db_config: Dict,
    concept_names: List[str],
    use_graph: bool = True
) -> Tuple[str, int, bool, List[Dict]]:
    """
    Process a single video (for parallel execution).
    Each call creates its own connections.

    Returns: (video_id, concept_count, success, new_concepts)
    """
    title = video["title"]
    url = video["url"]
    video_id = generate_video_id(title, url)

    # Create per-thread connections
    conn = psycopg2.connect(**db_config)
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    processor = VideoProcessorAssemblyAI()

    graph_db = None
    if use_graph:
        try:
            graph_db = PokerGraphDB()
            if not graph_db.verify_connection():
                graph_db = None
        except:
            graph_db = None

    try:
        # 1. Transcribe
        transcript, chunks = processor.process_video(
            video_path=video["mp3_path"],
            video_id=video_id,
            title=title,
            url=url,
            chunk_duration=60.0,
            overlap=10.0,
            use_chapters=False
        )

        # 2. Save to PostgreSQL
        save_video_to_db(
            conn=conn,
            video_id=video_id,
            title=title,
            url=url,
            category=video["category"],
            chunks=chunks,
            openai_client=openai_client
        )

        # 3. Extract concepts
        known_concepts, new_concepts = extract_concepts_for_video(
            title=title,
            chunks=chunks,
            concept_names=concept_names,
            openai_client=openai_client
        )

        # 4. Handle NEW concepts
        for nc in new_concepts:
            if add_concept_to_taxonomy(nc):
                if graph_db:
                    sync_concept_to_neo4j(nc, graph_db)

        # 5. Update Neo4j
        if graph_db:
            graph_db.create_video(VideoNode(
                id=video_id,
                title=title,
                url=url,
                category=video["category"]
            ))

            for c in known_concepts:
                if c["name"] in concept_names:
                    try:
                        graph_db.video_mentions_concept(video_id, c["name"], c["weight"])
                    except:
                        pass

            for nc in new_concepts:
                try:
                    graph_db.video_mentions_concept(video_id, nc["name"], 0.7)
                except:
                    pass

        return (video_id, len(known_concepts) + len(new_concepts), True, new_concepts)

    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        return (video_id, 0, False, [])

    finally:
        conn.close()
        if graph_db:
            graph_db.close()


def batch_process(
    folder_path: str,
    dry_run: bool = False,
    skip_existing: bool = True,
    limit: int = 0,
    parallel: int = 1
):
    """Main batch processing function with parallel support"""

    print("=" * 60)
    print("Batch Video Processor")
    print("=" * 60)
    print(f"Folder: {folder_path}")
    print(f"Dry run: {dry_run}")
    print(f"Skip existing: {skip_existing}")
    print(f"Parallel workers: {parallel}")
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
        if len(videos) > 20:
            print(f"  ... and {len(videos) - 20} more")
        return

    # Initialize services (for checking existing)
    print("Initializing services...")

    db_config = get_db_config()
    conn = psycopg2.connect(**db_config)
    print(f"  PostgreSQL: connected ({db_config['host']})")

    # Check Neo4j availability
    use_graph = False
    try:
        graph_db = PokerGraphDB()
        if graph_db.verify_connection():
            print("  Neo4j: connected")
            use_graph = True
        graph_db.close()
    except:
        print("  Neo4j: not available (will skip graph updates)")

    taxonomy = PokerTaxonomy()
    concept_names = [c.get("name") for c in taxonomy.concepts.values()]
    print(f"  Taxonomy: {len(concept_names)} concepts")
    print()

    # Get existing videos
    existing_ids = get_existing_video_ids(conn) if skip_existing else set()
    print(f"Existing videos in DB: {len(existing_ids)}")
    conn.close()

    # Filter videos to process
    videos_to_process = []
    skipped = 0
    for video in videos:
        video_id = generate_video_id(video["title"], video["url"])
        if skip_existing and video_id in existing_ids:
            skipped += 1
        else:
            videos_to_process.append(video)

    print(f"Videos to process: {len(videos_to_process)}")
    print(f"Already skipped: {skipped}")
    print()

    if not videos_to_process:
        print("All videos already processed!")
        return

    # Apply limit
    if limit > 0:
        videos_to_process = videos_to_process[:limit]
        print(f"Limited to: {len(videos_to_process)} videos")
        print()

    # Process videos
    processed = 0
    failed = 0
    new_concepts_added = 0

    if parallel > 1:
        # PARALLEL processing
        print(f"Processing with {parallel} parallel workers...")
        print()

        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = {
                executor.submit(
                    process_single_video,
                    video,
                    db_config,
                    concept_names,
                    use_graph
                ): video for video in videos_to_process
            }

            pbar = tqdm(as_completed(futures), total=len(videos_to_process), desc="Processing", unit="video")
            for future in pbar:
                video = futures[future]
                try:
                    video_id, concept_count, success, new_concepts = future.result()
                    if success:
                        processed += 1
                        for nc in new_concepts:
                            tqdm.write(f"  + NEW CONCEPT: {nc['name']}")
                            new_concepts_added += 1
                        pbar.set_postfix(done=processed, failed=failed)
                    else:
                        failed += 1
                        tqdm.write(f"  ✗ Failed: {video['title'][:40]}")
                except Exception as e:
                    failed += 1
                    tqdm.write(f"  ✗ Error [{video['title'][:30]}]: {e}")

    else:
        # SEQUENTIAL processing
        conn = psycopg2.connect(**db_config)
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        processor = VideoProcessorAssemblyAI()

        graph_db = None
        if use_graph:
            try:
                graph_db = PokerGraphDB()
                if not graph_db.verify_connection():
                    graph_db = None
            except:
                pass

        pbar = tqdm(videos_to_process, desc="Processing videos", unit="video")

        for video in pbar:
            title = video["title"]
            url = video["url"]
            video_id = generate_video_id(title, url)

            pbar.set_description(f"Processing: {title[:40]}...")

            try:
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

                pbar.set_postfix(step="analyzing concepts")
                known_concepts, new_concepts = extract_concepts_for_video(
                    title=title,
                    chunks=chunks,
                    concept_names=concept_names,
                    openai_client=openai_client
                )

                if new_concepts:
                    for nc in new_concepts:
                        if add_concept_to_taxonomy(nc):
                            tqdm.write(f"  + NEW CONCEPT: {nc['name']}")
                            new_concepts_added += 1
                            concept_names.append(nc["name"])
                            if graph_db:
                                sync_concept_to_neo4j(nc, graph_db)

                if graph_db:
                    pbar.set_postfix(step="updating graph")
                    graph_db.create_video(VideoNode(
                        id=video_id,
                        title=title,
                        url=url,
                        category=video["category"]
                    ))

                    for c in known_concepts:
                        if c["name"] in concept_names:
                            graph_db.video_mentions_concept(video_id, c["name"], c["weight"])

                    for nc in new_concepts:
                        graph_db.video_mentions_concept(video_id, nc["name"], 0.7)

                processed += 1
                pbar.set_postfix(status="done", concepts=len(known_concepts) + len(new_concepts))

            except Exception as e:
                tqdm.write(f"  ✗ Error [{title[:30]}]: {e}")
                try:
                    conn.rollback()
                except:
                    pass
                failed += 1

        pbar.close()
        conn.close()
        if graph_db:
            graph_db.close()

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
    try:
        conn = psycopg2.connect(**db_config)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM videos")
            total_videos = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM transcripts")
            total_chunks = cur.fetchone()[0]
        conn.close()

        print(f"Total videos in DB: {total_videos}")
        print(f"Total chunks in DB: {total_chunks}")
    except Exception as e:
        print(f"Could not get final stats: {e}")

    if use_graph:
        try:
            graph_db = PokerGraphDB()
            stats = graph_db.get_stats()
            print(f"Neo4j - Videos: {stats['videos']}, Mentions: {stats['mentions']}")
            graph_db.close()
        except:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch process videos from folder")
    parser.add_argument("--folder", required=True, help="Folder with MP3 and TXT files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")
    parser.add_argument("--skip-existing", action="store_true", default=True,
                       help="Skip videos already in database (default: True)")
    parser.add_argument("--no-skip", action="store_true", help="Process all videos even if exist")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of videos to process")
    parser.add_argument("--parallel", type=int, default=1,
                       help="Number of parallel workers (default: 1)")

    args = parser.parse_args()

    skip_existing = not args.no_skip

    batch_process(
        folder_path=args.folder,
        dry_run=args.dry_run,
        skip_existing=skip_existing,
        limit=args.limit,
        parallel=args.parallel
    )
