#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Export Neo4j Knowledge Graph to Obsidian vault.

Structure:
  vault/
  ├── Concepts/
  │   ├── 3-Bet.md
  │   ├── Squeeze.md
  │   └── ...
  └── Videos/
      ├── 3-Betting Preflop.md
      └── ...

Concept files contain:
  - Frontmatter (category, difficulty)
  - Related concepts as [[links]]
  - Builds on (prerequisites) as [[links]]
  - Videos that mention this concept

Video files contain:
  - Frontmatter (url, category)
  - Concepts mentioned as [[links]] with weights
"""

import os
import re
import argparse
from pathlib import Path
from lib.graph_db import PokerGraphDB


def sanitize_filename(name: str) -> str:
    """Make name safe for filesystem"""
    # Replace problematic characters
    name = re.sub(r'[<>:"/\\|?*]', '-', name)
    return name.strip()


def export_to_obsidian(vault_path: str):
    """Export Neo4j graph to Obsidian vault"""

    vault = Path(vault_path)
    concepts_dir = vault / "Concepts"
    videos_dir = vault / "Videos"

    # Create directories
    concepts_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    db = PokerGraphDB()

    print(f"Exporting to: {vault}")

    # =========================================================================
    # Export Concepts
    # =========================================================================

    with db.driver.session(database=db.database) as session:
        # Get all concepts with their relationships
        result = session.run("""
            MATCH (c:Concept)
            OPTIONAL MATCH (c)-[:RELATES_TO]->(related:Concept)
            OPTIONAL MATCH (c)-[:BUILDS_ON]->(prereq:Concept)
            OPTIONAL MATCH (v:Video)-[m:MENTIONS]->(c)
            RETURN c.name as name,
                   c.category as category,
                   c.difficulty as difficulty,
                   COLLECT(DISTINCT related.name) as relates_to,
                   COLLECT(DISTINCT prereq.name) as builds_on,
                   COLLECT(DISTINCT {title: v.title, weight: m.weight}) as mentioned_in
        """)

        concepts_count = 0
        for record in result:
            name = record["name"]
            category = record["category"] or "unknown"
            difficulty = record["difficulty"] or ""
            relates_to = [r for r in record["relates_to"] if r]
            builds_on = [b for b in record["builds_on"] if b]
            mentioned_in = [m for m in record["mentioned_in"] if m["title"]]

            # Build markdown content
            content = f"""---
type: concept
category: {category}
difficulty: {difficulty}
---

# {name}

## Related Concepts
"""
            if relates_to:
                for r in sorted(relates_to):
                    content += f"- [[{r}]]\n"
            else:
                content += "_No related concepts_\n"

            content += """
## Prerequisites (Builds On)
"""
            if builds_on:
                for b in sorted(builds_on):
                    content += f"- [[{b}]]\n"
            else:
                content += "_No prerequisites_\n"

            content += """
## Videos About This Concept
"""
            if mentioned_in:
                # Sort by weight descending
                sorted_videos = sorted(mentioned_in, key=lambda x: x["weight"] or 0, reverse=True)
                for v in sorted_videos:
                    weight = v["weight"] or 0
                    importance = "★★★" if weight >= 0.8 else "★★" if weight >= 0.5 else "★"
                    content += f"- {importance} [[{v['title']}]] (weight: {weight:.1f})\n"
            else:
                content += "_No videos mention this concept_\n"

            # Write file
            filename = sanitize_filename(name) + ".md"
            filepath = concepts_dir / filename
            filepath.write_text(content, encoding="utf-8")
            concepts_count += 1

        print(f"  Concepts: {concepts_count} files")

    # =========================================================================
    # Export Videos
    # =========================================================================

    with db.driver.session(database=db.database) as session:
        result = session.run("""
            MATCH (v:Video)
            OPTIONAL MATCH (v)-[m:MENTIONS]->(c:Concept)
            RETURN v.id as id,
                   v.title as title,
                   v.url as url,
                   v.category as category,
                   COLLECT({concept: c.name, weight: m.weight}) as concepts
        """)

        videos_count = 0
        for record in result:
            title = record["title"]
            url = record["url"] or ""
            category = record["category"] or "unknown"
            video_id = record["id"]
            concepts = [c for c in record["concepts"] if c["concept"]]

            content = f"""---
type: video
id: {video_id}
category: {category}
url: {url}
---

# {title}

## Concepts Mentioned

"""
            if concepts:
                # Sort by weight descending
                sorted_concepts = sorted(concepts, key=lambda x: x["weight"] or 0, reverse=True)

                content += "| Concept | Weight | Importance |\n"
                content += "|---------|--------|------------|\n"

                for c in sorted_concepts:
                    weight = c["weight"] or 0
                    importance = "Main topic" if weight >= 0.8 else "Discussed" if weight >= 0.5 else "Mentioned"
                    content += f"| [[{c['concept']}]] | {weight:.1f} | {importance} |\n"
            else:
                content += "_No concepts linked_\n"

            content += f"""

## Source

- URL: {url}
- Category: {category}
"""

            # Write file
            filename = sanitize_filename(title) + ".md"
            filepath = videos_dir / filename
            filepath.write_text(content, encoding="utf-8")
            videos_count += 1

        print(f"  Videos: {videos_count} files")

    db.close()

    # Create index file
    index_content = f"""# RangeLab Knowledge Graph

Exported from Neo4j.

## Folders

- [[Concepts/]] - {concepts_count} poker concepts
- [[Videos/]] - {videos_count} educational videos

## How to Edit

1. **Add relationship**: Add `[[Concept Name]]` link in Related Concepts section
2. **Add prerequisite**: Add `[[Concept Name]]` link in Prerequisites section
3. **Link video to concept**: Add row in Concepts Mentioned table
4. **Change weight**: Edit the weight value (0.0-1.0)

## Re-import

After editing, run:
```bash
python obsidian_import.py --vault "{vault_path}"
```

## Legend

- ★★★ = Main topic (weight >= 0.8)
- ★★ = Discussed (weight >= 0.5)
- ★ = Mentioned (weight < 0.5)
"""

    (vault / "README.md").write_text(index_content, encoding="utf-8")

    print(f"\nDone! Open vault in Obsidian: {vault}")
    print(f"After editing, run: python obsidian_import.py --vault \"{vault_path}\"")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export Neo4j graph to Obsidian")
    parser.add_argument("--vault", required=True, help="Path to Obsidian vault")
    args = parser.parse_args()

    export_to_obsidian(args.vault)
