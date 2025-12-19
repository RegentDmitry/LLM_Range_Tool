#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RAG system for searching video transcripts
Uses ChromaDB for vector storage and OpenAI for embeddings
"""

import os
from typing import List, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from models.video_models import VideoChunk, SearchResult, VideoMetadata


class VideoRAG:
    """RAG system for video search"""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        collection_name: str = "video_transcripts",
        persist_directory: str = "./chroma_db"
    ):
        """
        Initialize RAG system

        Args:
            openai_api_key: OpenAI API key
            collection_name: ChromaDB collection name
            persist_directory: Directory for ChromaDB data storage
        """
        # OpenAI client for embeddings
        api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key not found")

        self.openai_client = OpenAI(api_key=api_key)

        # ChromaDB client
        persist_path = Path(persist_directory)
        persist_path.mkdir(parents=True, exist_ok=True)

        self.chroma_client = chromadb.PersistentClient(
            path=str(persist_path),
            settings=Settings(anonymized_telemetry=False)
        )

        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Video transcript chunks for RAG search"}
        )

        print(f"✓ ChromaDB initialized: {persist_directory}")
        print(f"✓ Collection: {collection_name}")

    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings via OpenAI API

        Args:
            texts: List of texts to vectorize

        Returns:
            List of embedding vectors
        """
        print(f"🔢 Creating embeddings for {len(texts)} texts...")

        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small",  # $0.02 / 1M tokens
            input=texts
        )

        embeddings = [item.embedding for item in response.data]
        print(f"✓ Embeddings created: {len(embeddings)} vectors")

        return embeddings

    def add_chunks(self, chunks: List[VideoChunk]) -> None:
        """
        Add video chunks to vector DB

        Args:
            chunks: List of VideoChunk to index
        """
        if not chunks:
            print("⚠️  No chunks to add")
            return

        print(f"📥 Adding {len(chunks)} chunks to vector DB...")

        # Prepare data
        ids = [chunk.chunk_id for chunk in chunks]
        texts = [chunk.text for chunk in chunks]
        metadatas = [
            VideoMetadata(
                video_id=chunk.video_id,
                video_title=chunk.video_title,
                video_url=chunk.video_url,
                chunk_id=chunk.chunk_id,
                start_time=chunk.start_time,
                end_time=chunk.end_time,
                timestamp=chunk.timestamp,
                text=chunk.text,
                url_with_timestamp=chunk.url_with_timestamp
            ).model_dump()
            for chunk in chunks
        ]

        # Create embeddings
        embeddings = self.create_embeddings(texts)

        # Add to ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )

        print(f"✓ {len(chunks)} chunks successfully added to DB")

    def search(
        self,
        query: str,
        top_k: int = 5,
        video_id: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search video transcripts

        Args:
            query: Search query
            top_k: Number of results
            video_id: Filter by video ID (optional)

        Returns:
            List of SearchResult with found chunks
        """
        print(f"🔍 Searching for: '{query}'")

        # Create embedding for query
        query_embedding = self.create_embeddings([query])[0]

        # Build filter
        where = {"video_id": video_id} if video_id else None

        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )

        # Parse results
        search_results = []
        if results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                metadata = results['metadatas'][0][i]

                # Restore VideoChunk from metadata
                chunk = VideoChunk(
                    chunk_id=metadata['chunk_id'],
                    video_id=metadata['video_id'],
                    video_title=metadata['video_title'],
                    video_url=metadata['video_url'],
                    start_time=metadata['start_time'],
                    end_time=metadata['end_time'],
                    text=metadata['text']
                )

                # Distance from ChromaDB (lower = better)
                # Convert to score (higher = better)
                distance = results['distances'][0][i]
                score = 1 / (1 + distance)  # Normalization

                search_results.append(SearchResult(chunk=chunk, score=score))

        print(f"✓ Found {len(search_results)} results")

        return search_results

    def get_stats(self) -> dict:
        """
        Get vector DB statistics

        Returns:
            Dictionary with statistics
        """
        count = self.collection.count()

        # Get all metadata for stats
        if count > 0:
            all_data = self.collection.get(include=["metadatas"])
            video_ids = set(m['video_id'] for m in all_data['metadatas'])
            unique_videos = len(video_ids)
        else:
            unique_videos = 0

        return {
            "total_chunks": count,
            "unique_videos": unique_videos,
            "collection_name": self.collection.name
        }

    def clear_collection(self) -> None:
        """Clear collection (delete all data)"""
        print("⚠️  Clearing collection...")

        # Delete and recreate
        self.chroma_client.delete_collection(name=self.collection.name)
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection.name,
            metadata={"description": "Video transcript chunks for RAG search"}
        )

        print("✓ Collection cleared")


__all__ = ['VideoRAG']
