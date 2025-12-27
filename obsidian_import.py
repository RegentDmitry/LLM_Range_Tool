#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Import Obsidian vault back to Neo4j.

Reads markdown files and updates:
- RELATES_TO relationships between concepts
- BUILDS_ON relationships (prerequisites)
- MENTIONS relationships (video -> concept with weight)

Usage:
    python obsidian_import.py --vault "C:/JN/obsidian/jnandez"
    python obsidian_import.py --vault "C:/JN/obsidian/jnandez" --dry-run
"""

import os
import re
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from lib.graph_db import PokerGraphDB


def parse_frontmatter(content: str) -> Tuple[Dict, str]:
    """Parse YAML frontmatter from markdown"""
    frontmatter = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1].strip()
            body = parts[2].strip()

            for line in fm_text.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    frontmatter[key.strip()] = value.strip()

    return frontmatter, body


def extract_wiki_links(text: str) -> List[str]:
    """Extract [[wiki links]] from text"""
    pattern = r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]'
    return re.findall(pattern, text)


def parse_concept_file(filepath: Path) -> Dict:
    """Parse concept markdown file"""
    content = filepath.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)

    name = filepath.stem  # filename without extension

    # Find sections
    relates_to = []
    builds_on = []

    current_section = None
    for line in body.split("\n"):
        line_lower = line.lower().strip()

        if "## related" in line_lower:
            current_section = "relates_to"
        elif "## prerequisite" in line_lower or "## builds on" in line_lower:
            current_section = "builds_on"
        elif "## video" in line_lower:
            current_section = "videos"
        elif line.startswith("## "):
            current_section = None
        elif current_section == "relates_to":
            links = extract_wiki_links(line)
            relates_to.extend(links)
        elif current_section == "builds_on":
            links = extract_wiki_links(line)
            builds_on.extend(links)

    return {
        "name": name,
        "category": frontmatter.get("category", "unknown"),
        "difficulty": frontmatter.get("difficulty", ""),
        "relates_to": relates_to,
        "builds_on": builds_on
    }


def parse_video_file(filepath: Path) -> Dict:
    """Parse video markdown file"""
    content = filepath.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)

    title = filepath.stem
    video_id = frontmatter.get("id", "")

    # Parse concepts table
    concepts = []

    # Look for table rows: | [[Concept]] | 0.7 | ... |
    table_pattern = r'\|\s*\[\[([^\]]+)\]\]\s*\|\s*([\d.]+)\s*\|'
    for match in re.finditer(table_pattern, body):
        concept_name = match.group(1)
        weight = float(match.group(2))
        concepts.append({"concept": concept_name, "weight": weight})

    return {
        "id": video_id,
        "title": title,
        "url": frontmatter.get("url", ""),
        "category": frontmatter.get("category", "unknown"),
        "concepts": concepts
    }


def import_from_obsidian(vault_path: str, dry_run: bool = False):
    """Import Obsidian vault to Neo4j"""

    vault = Path(vault_path)
    concepts_dir = vault / "Concepts"
    videos_dir = vault / "Videos"

    if not vault.exists():
        print(f"Error: Vault not found: {vault}")
        return

    print(f"Importing from: {vault}")
    if dry_run:
        print("DRY RUN - no changes will be made to Neo4j")
    print()

    db = PokerGraphDB() if not dry_run else None

    # =========================================================================
    # Parse all concept files
    # =========================================================================

    concepts = []
    if concepts_dir.exists():
        for filepath in concepts_dir.glob("*.md"):
            try:
                concept = parse_concept_file(filepath)
                concepts.append(concept)
            except Exception as e:
                print(f"  Warning: Failed to parse {filepath}: {e}")

    print(f"Parsed {len(concepts)} concept files")

    # =========================================================================
    # Parse all video files
    # =========================================================================

    videos = []
    if videos_dir.exists():
        for filepath in videos_dir.glob("*.md"):
            try:
                video = parse_video_file(filepath)
                if video["id"]:  # Only if has valid ID
                    videos.append(video)
            except Exception as e:
                print(f"  Warning: Failed to parse {filepath}: {e}")

    print(f"Parsed {len(videos)} video files")
    print()

    # =========================================================================
    # Sync to Neo4j
    # =========================================================================

    if dry_run:
        print("Changes that would be made:")
        print()

        for c in concepts:
            if c["relates_to"]:
                print(f"  {c['name']} --RELATES_TO--> {c['relates_to']}")
            if c["builds_on"]:
                print(f"  {c['name']} --BUILDS_ON--> {c['builds_on']}")

        for v in videos:
            if v["concepts"]:
                print(f"  {v['title'][:40]}... --MENTIONS--> {[c['concept'] for c in v['concepts']]}")

        print()
        print("Run without --dry-run to apply changes")
        return

    # Clear existing relationships and rebuild
    print("Updating Neo4j...")

    with db.driver.session(database=db.database) as session:
        # Clear RELATES_TO and BUILDS_ON (will rebuild from Obsidian)
        print("  Clearing RELATES_TO relationships...")
        session.run("MATCH ()-[r:RELATES_TO]->() DELETE r")

        print("  Clearing BUILDS_ON relationships...")
        session.run("MATCH ()-[r:BUILDS_ON]->() DELETE r")

        print("  Clearing MENTIONS relationships...")
        session.run("MATCH ()-[r:MENTIONS]->() DELETE r")

    # Rebuild from Obsidian data
    relates_count = 0
    builds_count = 0
    mentions_count = 0

    for c in concepts:
        # RELATES_TO
        for related in c["relates_to"]:
            try:
                db.concept_relates_to(c["name"], related)
                relates_count += 1
            except:
                pass  # Concept might not exist

        # BUILDS_ON
        for prereq in c["builds_on"]:
            try:
                db.concept_builds_on(c["name"], prereq)
                builds_count += 1
            except:
                pass

    for v in videos:
        for c in v["concepts"]:
            try:
                db.video_mentions_concept(v["id"], c["concept"], c["weight"])
                mentions_count += 1
            except:
                pass

    print()
    print(f"Created relationships:")
    print(f"  RELATES_TO: {relates_count}")
    print(f"  BUILDS_ON: {builds_count}")
    print(f"  MENTIONS: {mentions_count}")

    # Final stats
    stats = db.get_stats()
    print()
    print(f"Final Neo4j stats:")
    print(f"  Videos: {stats['videos']}")
    print(f"  Concepts: {stats['concepts']}")
    print(f"  MENTIONS: {stats['mentions']}")
    print(f"  RELATES_TO: {stats['relates_to']}")
    print(f"  BUILDS_ON: {stats['builds_on']}")

    db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import Obsidian vault to Neo4j")
    parser.add_argument("--vault", required=True, help="Path to Obsidian vault")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    args = parser.parse_args()

    import_from_obsidian(args.vault, dry_run=args.dry_run)
