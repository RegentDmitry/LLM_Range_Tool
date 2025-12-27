#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Populate Neo4j Knowledge Graph with data from:
1. PostgreSQL (videos, transcripts)
2. Taxonomy (concepts, relationships)
3. LLM analysis (video -> concept MENTIONS)
"""

import os
import json
import psycopg2
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI

from lib.graph_db import PokerGraphDB, VideoNode, ConceptNode
from lib.taxonomy import PokerTaxonomy

load_dotenv()


# Database config - use Windows host IP from WSL
# Get Windows IP: ip route | grep default | awk '{print $3}'
DB_CONFIG = {
    "host": "172.24.192.1",  # Windows host from WSL
    "port": 5432,
    "database": "rangelab",
    "user": "postgres",
    "password": "dbpass"
}


def load_videos_from_postgres() -> List[Dict[str, Any]]:
    """Load all videos from PostgreSQL"""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
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
    finally:
        conn.close()


def load_transcripts_for_video(video_id: str) -> str:
    """Load all transcript chunks for a video, concatenated"""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT text
                FROM transcripts
                WHERE video_id = %s
                ORDER BY timestamp
            """, (video_id,))
            chunks = [row[0] for row in cur.fetchall()]
            return " ".join(chunks)
    finally:
        conn.close()


def extract_concepts_with_llm(
    video_title: str,
    transcript: str,
    available_concepts: List[str],
    openai_client: OpenAI
) -> List[Dict[str, Any]]:
    """
    Use LLM to extract which concepts are mentioned in the video.
    Returns list of {concept: str, weight: float}
    """
    # Truncate transcript if too long
    max_chars = 12000  # ~3000 tokens
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "..."

    prompt = f"""Analyze this poker video transcript and identify which concepts from the list are discussed.

VIDEO TITLE: {video_title}

TRANSCRIPT:
{transcript}

AVAILABLE CONCEPTS (only choose from these):
{', '.join(available_concepts)}

For each concept that is discussed in the video, rate its importance:
- 1.0 = Main topic of the video
- 0.7 = Significantly discussed
- 0.4 = Mentioned/touched upon
- 0.2 = Briefly referenced

Return JSON format:
{{"concepts": [{{"name": "concept_name", "weight": 0.7}}, ...]}}

Only include concepts that are actually discussed. Return empty list if no matches."""

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
        print(f"    Error extracting concepts: {e}")
        return []


def populate_graph():
    """Main function to populate the knowledge graph"""

    print("=" * 60)
    print("Populating Neo4j Knowledge Graph")
    print("=" * 60)

    # Initialize connections
    graph_db = PokerGraphDB()
    taxonomy = PokerTaxonomy()
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    if not graph_db.verify_connection():
        print("Failed to connect to Neo4j!")
        return

    print("\n[Step 1] Loading concepts from taxonomy...")

    # Get all concept names
    concept_names = []
    for concept_key, concept_data in taxonomy.concepts.items():
        name = concept_data.get("name", concept_key)
        category = concept_data.get("category", "unknown")
        difficulty = concept_data.get("difficulty")

        # Create concept node
        concept_node = ConceptNode(
            name=name,
            category=category,
            difficulty=difficulty
        )
        graph_db.create_concept(concept_node)
        concept_names.append(name)

    print(f"    Created {len(concept_names)} concept nodes")

    print("\n[Step 2] Creating RELATES_TO relationships...")

    # Create relationships from taxonomy
    relates_count = 0
    for concept_key, concept_data in taxonomy.concepts.items():
        name = concept_data.get("name", concept_key)
        related = concept_data.get("related", [])

        for related_name in related:
            # Find the actual concept name (might be an alias)
            related_concept = taxonomy.find_concept(related_name)
            if related_concept:
                actual_name = related_concept.get("name", related_name)
                graph_db.concept_relates_to(name, actual_name)
                relates_count += 1

    print(f"    Created {relates_count} RELATES_TO relationships")

    print("\n[Step 3] Loading videos from PostgreSQL...")

    videos = load_videos_from_postgres()
    print(f"    Found {len(videos)} videos")

    # Create video nodes
    for video in videos:
        video_node = VideoNode(
            id=video["id"],
            title=video["title"],
            url=video["url"],
            category=video["category"]
        )
        graph_db.create_video(video_node)

    print(f"    Created {len(videos)} video nodes")

    print("\n[Step 4] Analyzing videos with LLM to find MENTIONS...")

    mentions_count = 0
    for i, video in enumerate(videos, 1):
        print(f"\n    [{i}/{len(videos)}] {video['title']}")

        # Load transcript
        transcript = load_transcripts_for_video(video["id"])
        if not transcript:
            print("        No transcript found, skipping...")
            continue

        print(f"        Transcript: {len(transcript)} chars")

        # Extract concepts with LLM
        concepts = extract_concepts_with_llm(
            video["title"],
            transcript,
            concept_names,
            openai_client
        )

        if concepts:
            print(f"        Found {len(concepts)} concepts:")
            for c in concepts:
                concept_name = c.get("name", "")
                weight = c.get("weight", 0.5)

                # Verify concept exists
                if concept_name in concept_names:
                    graph_db.video_mentions_concept(video["id"], concept_name, weight)
                    mentions_count += 1
                    print(f"          - {concept_name} (weight: {weight})")
                else:
                    print(f"          - {concept_name} (not in taxonomy, skipped)")
        else:
            print("        No concepts found")

    print("\n" + "=" * 60)
    print("Graph Population Complete!")
    print("=" * 60)

    # Get stats
    stats = graph_db.get_stats()
    print(f"\nFinal Graph Statistics:")
    print(f"  Videos: {stats['videos']}")
    print(f"  Concepts: {stats['concepts']}")
    print(f"  MENTIONS: {stats['mentions']}")
    print(f"  RELATES_TO: {stats['relates_to']}")
    print(f"  BUILDS_ON: {stats['builds_on']}")

    graph_db.close()


def add_builds_on_relationships():
    """
    Add BUILDS_ON relationships for learning progression.
    These define which concepts should be learned before others.
    """

    print("\nAdding BUILDS_ON relationships for learning progression...")

    graph_db = PokerGraphDB()

    # Define learning progressions (advanced -> basic)
    progressions = [
        # Preflop actions build on each other
        ("3-Bet", "Raise First In"),
        ("4-Bet", "3-Bet"),
        ("5-Bet", "4-Bet"),
        ("Squeeze", "3-Bet"),
        ("Cold 4-Bet", "4-Bet"),
        ("Cold Call", "Raise First In"),
        ("Back-Raise", "Limp"),
        ("Facing a 3-Bet", "3-Bet"),
        ("Facing a Squeeze", "Squeeze"),

        # Positions build on understanding
        ("Cutoff", "Button"),
        ("Hijack", "Cutoff"),
        ("Lojack", "Hijack"),
        ("In Position", "Button"),
        ("Out of Position", "In Position"),
        ("Defending the BB", "Big Blind"),

        # Stack concepts
        ("Stack to Pot Ratio", "Short Stack"),
        ("Stack to Pot Ratio", "Deep Stack"),

        # Strategy concepts
        ("GTO", "Equity Realization"),
        ("Exploitative", "GTO"),
        ("Range Advantage", "Equity Realization"),
        ("Nut Advantage", "Range Advantage"),
        ("Blockers", "Combinatorics"),

        # Postflop builds on preflop
        ("Continuation Bet", "Raise First In"),
        ("Check-Raise", "Out of Position"),
        ("Donk Bet", "Out of Position"),
        ("Overbet", "Nut Advantage"),

        # Situations
        ("3-Bet Pot", "3-Bet"),
        ("4-Bet Pot", "4-Bet"),

        # Hand types
        ("Double Suited", "Single Suited"),
        ("Broadway Pairs", "Aces"),

        # Streets
        ("Postflop", "Preflop"),
        ("Flop", "Preflop"),
        ("Turn", "Flop"),
        ("River", "Turn"),
    ]

    count = 0
    for advanced, basic in progressions:
        try:
            graph_db.concept_builds_on(advanced, basic)
            count += 1
            print(f"  {advanced} -> {basic}")
        except Exception as e:
            print(f"  Warning: {advanced} -> {basic}: {e}")

    print(f"\nCreated {count} BUILDS_ON relationships")

    stats = graph_db.get_stats()
    print(f"Total BUILDS_ON: {stats['builds_on']}")

    graph_db.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--builds-on":
        # Just add BUILDS_ON relationships
        add_builds_on_relationships()
    else:
        # Full population
        populate_graph()
        add_builds_on_relationships()
