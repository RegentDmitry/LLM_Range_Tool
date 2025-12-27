#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Neo4j Graph Database connection and operations
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()


@dataclass
class VideoNode:
    """Video node data"""
    id: str
    title: str
    url: str
    category: str


@dataclass
class ConceptNode:
    """Concept node data"""
    name: str
    category: str
    difficulty: Optional[str] = None


class PokerGraphDB:
    """
    Neo4j Graph Database for poker video knowledge graph.

    Schema:
        Nodes:
            (:Video {id, title, url, category})
            (:Concept {name, category, difficulty})

        Relationships:
            (Video)-[:MENTIONS {weight}]->(Concept)
            (Concept)-[:RELATES_TO]->(Concept)
            (Concept)-[:BUILDS_ON]->(Concept)
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None
    ):
        self.uri = uri or os.getenv("NEO4J_URI")
        self.username = username or os.getenv("NEO4J_USERNAME")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        self.database = database or os.getenv("NEO4J_DATABASE", "neo4j")

        if not all([self.uri, self.username, self.password]):
            raise ValueError("Neo4j credentials not found. Set NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD")

        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.username, self.password)
        )

    def close(self):
        """Close database connection"""
        self.driver.close()

    def verify_connection(self) -> bool:
        """Test connection to Neo4j"""
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 as test")
                return result.single()["test"] == 1
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def init_schema(self):
        """Create indexes and constraints for optimal performance"""
        with self.driver.session(database=self.database) as session:
            # Unique constraint on Video.id
            session.run("""
                CREATE CONSTRAINT video_id IF NOT EXISTS
                FOR (v:Video) REQUIRE v.id IS UNIQUE
            """)

            # Unique constraint on Concept.name
            session.run("""
                CREATE CONSTRAINT concept_name IF NOT EXISTS
                FOR (c:Concept) REQUIRE c.name IS UNIQUE
            """)

            # Index for faster lookups
            session.run("""
                CREATE INDEX video_title IF NOT EXISTS
                FOR (v:Video) ON (v.title)
            """)

            session.run("""
                CREATE INDEX concept_category IF NOT EXISTS
                FOR (c:Concept) ON (c.category)
            """)

        print("Schema initialized: constraints and indexes created")

    def clear_all(self):
        """Delete all nodes and relationships (use with caution!)"""
        with self.driver.session(database=self.database) as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("All nodes and relationships deleted")

    # =========================================================================
    # Video operations
    # =========================================================================

    def create_video(self, video: VideoNode) -> None:
        """Create or update a Video node"""
        with self.driver.session(database=self.database) as session:
            session.run("""
                MERGE (v:Video {id: $id})
                SET v.title = $title,
                    v.url = $url,
                    v.category = $category
            """, id=video.id, title=video.title, url=video.url, category=video.category)

    def get_all_videos(self) -> List[Dict[str, Any]]:
        """Get all videos"""
        with self.driver.session(database=self.database) as session:
            result = session.run("MATCH (v:Video) RETURN v")
            return [dict(record["v"]) for record in result]

    # =========================================================================
    # Concept operations
    # =========================================================================

    def create_concept(self, concept: ConceptNode) -> None:
        """Create or update a Concept node"""
        with self.driver.session(database=self.database) as session:
            session.run("""
                MERGE (c:Concept {name: $name})
                SET c.category = $category,
                    c.difficulty = $difficulty
            """, name=concept.name, category=concept.category, difficulty=concept.difficulty)

    def get_all_concepts(self) -> List[Dict[str, Any]]:
        """Get all concepts"""
        with self.driver.session(database=self.database) as session:
            result = session.run("MATCH (c:Concept) RETURN c")
            return [dict(record["c"]) for record in result]

    # =========================================================================
    # Relationship operations
    # =========================================================================

    def video_mentions_concept(self, video_id: str, concept_name: str, weight: float = 1.0) -> None:
        """Create MENTIONS relationship between Video and Concept"""
        with self.driver.session(database=self.database) as session:
            session.run("""
                MATCH (v:Video {id: $video_id})
                MATCH (c:Concept {name: $concept_name})
                MERGE (v)-[r:MENTIONS]->(c)
                SET r.weight = $weight
            """, video_id=video_id, concept_name=concept_name, weight=weight)

    def concept_relates_to(self, concept1: str, concept2: str) -> None:
        """Create RELATES_TO relationship between two Concepts"""
        with self.driver.session(database=self.database) as session:
            session.run("""
                MATCH (c1:Concept {name: $concept1})
                MATCH (c2:Concept {name: $concept2})
                MERGE (c1)-[:RELATES_TO]->(c2)
            """, concept1=concept1, concept2=concept2)

    def concept_builds_on(self, advanced: str, basic: str) -> None:
        """Create BUILDS_ON relationship (advanced concept builds on basic)"""
        with self.driver.session(database=self.database) as session:
            session.run("""
                MATCH (a:Concept {name: $advanced})
                MATCH (b:Concept {name: $basic})
                MERGE (a)-[:BUILDS_ON]->(b)
            """, advanced=advanced, basic=basic)

    # =========================================================================
    # Query operations
    # =========================================================================

    def find_videos_by_concept(self, concept_name: str) -> List[Dict[str, Any]]:
        """Find all videos that mention a concept"""
        with self.driver.session(database=self.database) as session:
            result = session.run("""
                MATCH (v:Video)-[r:MENTIONS]->(c:Concept {name: $concept_name})
                RETURN v, r.weight as weight
                ORDER BY r.weight DESC
            """, concept_name=concept_name)
            return [{"video": dict(record["v"]), "weight": record["weight"]} for record in result]

    def find_videos_by_multiple_concepts(self, concepts: List[str]) -> List[Dict[str, Any]]:
        """Find videos that mention ALL given concepts"""
        with self.driver.session(database=self.database) as session:
            result = session.run("""
                MATCH (v:Video)
                WHERE ALL(concept IN $concepts WHERE
                    EXISTS { (v)-[:MENTIONS]->(:Concept {name: concept}) }
                )
                RETURN v,
                    SIZE([(v)-[:MENTIONS]->(c:Concept) WHERE c.name IN $concepts | c]) as match_count
                ORDER BY match_count DESC
            """, concepts=concepts)
            return [{"video": dict(record["v"]), "match_count": record["match_count"]} for record in result]

    def find_related_videos(self, video_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find videos related through shared concepts"""
        with self.driver.session(database=self.database) as session:
            result = session.run("""
                MATCH (v1:Video {id: $video_id})-[:MENTIONS]->(c:Concept)<-[:MENTIONS]-(v2:Video)
                WHERE v1 <> v2
                RETURN v2, COUNT(c) as shared_concepts, COLLECT(c.name) as concepts
                ORDER BY shared_concepts DESC
                LIMIT $limit
            """, video_id=video_id, limit=limit)
            return [
                {
                    "video": dict(record["v2"]),
                    "shared_concepts": record["shared_concepts"],
                    "concepts": record["concepts"]
                }
                for record in result
            ]

    def find_learning_path(self, target_concept: str) -> List[Dict[str, Any]]:
        """Find prerequisite concepts (what to learn before target)"""
        with self.driver.session(database=self.database) as session:
            result = session.run("""
                MATCH path = (target:Concept {name: $target})-[:BUILDS_ON*1..3]->(prereq:Concept)
                RETURN prereq.name as concept, LENGTH(path) as depth
                ORDER BY depth DESC
            """, target=target_concept)
            return [{"concept": record["concept"], "depth": record["depth"]} for record in result]

    def get_stats(self) -> Dict[str, int]:
        """Get graph statistics"""
        with self.driver.session(database=self.database) as session:
            # Count each separately to handle empty graph
            videos = session.run("MATCH (v:Video) RETURN COUNT(v) as count").single()["count"]
            concepts = session.run("MATCH (c:Concept) RETURN COUNT(c) as count").single()["count"]
            mentions = session.run("MATCH ()-[r:MENTIONS]->() RETURN COUNT(r) as count").single()["count"]
            relates = session.run("MATCH ()-[r:RELATES_TO]->() RETURN COUNT(r) as count").single()["count"]
            builds = session.run("MATCH ()-[r:BUILDS_ON]->() RETURN COUNT(r) as count").single()["count"]

            return {
                "videos": videos,
                "concepts": concepts,
                "mentions": mentions,
                "relates_to": relates,
                "builds_on": builds
            }


# =============================================================================
# Test connection
# =============================================================================

if __name__ == "__main__":
    print("Testing Neo4j connection...")

    db = PokerGraphDB()

    if db.verify_connection():
        print("✓ Connected to Neo4j Aura!")

        # Initialize schema
        db.init_schema()

        # Get stats
        stats = db.get_stats()
        print(f"\nGraph stats:")
        print(f"  Videos: {stats['videos']}")
        print(f"  Concepts: {stats['concepts']}")
        print(f"  MENTIONS: {stats['mentions']}")
        print(f"  RELATES_TO: {stats['relates_to']}")
        print(f"  BUILDS_ON: {stats['builds_on']}")
    else:
        print("✗ Connection failed!")

    db.close()
