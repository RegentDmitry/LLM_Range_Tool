#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Conversational RAG system using Pydantic AI
PostgreSQL + pgvector for vector search
"""

import os
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

import psycopg2
from .taxonomy import get_taxonomy
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from openai import OpenAI


# ============================================================================
# Data Models (Type-safe)
# ============================================================================

class VideoSource(BaseModel):
    """Source video information"""
    video_title: str
    timestamp: str
    url: str
    text: str
    relevance: float


class SearchResult(BaseModel):
    """Search result with answer and sources"""
    answer: str = Field(description="Answer to the user's question based on video content")
    sources: List[VideoSource] = Field(description="Video sources used for the answer")
    confidence: float = Field(description="Confidence score 0-1", ge=0, le=1)


class ConversationMessage(BaseModel):
    """Single conversation message"""
    role: str  # "user" or "assistant"
    content: str


class TranslatedQuery(BaseModel):
    """Query with optional translation"""
    original: str
    translated: str
    source_language: str  # "en", "ru", etc.


# ============================================================================
# Dependencies (injected into agent)
# ============================================================================

@dataclass
class RAGDependencies:
    """Dependencies for RAG agent"""
    db_connection: Any
    openai_client: OpenAI
    conversation_history: List[ConversationMessage]


# ============================================================================
# Database Configuration
# ============================================================================

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "rangelab",
    "user": "postgres",
    "password": "dbpass"
}


# ============================================================================
# Conversational RAG Class
# ============================================================================

class ConversationalVideoRAG:
    """
    Conversational RAG for poker video search
    Uses PostgreSQL + pgvector for vector search
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        model_name: str = "gpt-4o",
        temperature: float = 0.7
    ):
        """
        Initialize Conversational RAG

        Args:
            openai_api_key: OpenAI API key
            model_name: LLM model (gpt-4o-mini, gpt-4o, gpt-4)
            temperature: LLM temperature (0-1)
        """
        self.api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found")

        self.model_name = model_name
        self.temperature = temperature

        # OpenAI client for embeddings
        self.openai_client = OpenAI(api_key=self.api_key)

        # PostgreSQL connection
        self.conn = psycopg2.connect(**DB_CONFIG)

        # Conversation history
        self.conversation_history: List[ConversationMessage] = []

        # Create Pydantic AI agent
        self.agent = self._create_agent()

        # Get stats
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM transcripts WHERE embedding IS NOT NULL")
            chunk_count = cur.fetchone()[0]

        print(f"Conversational RAG initialized (pgvector)")
        print(f"   Model: {model_name}")
        print(f"   Chunks with embeddings: {chunk_count}")

    def _create_agent(self) -> Agent:
        """Create Pydantic AI agent with tools"""

        model = OpenAIModel(self.model_name)

        agent = Agent(
            model,
            output_type=SearchResult,
            system_prompt=self._get_system_prompt(),
            deps_type=RAGDependencies,
        )

        # Register search tool
        @agent.tool
        async def search_videos(
            ctx: RunContext[RAGDependencies],
            query: str,
            top_k: int = 5
        ) -> str:
            """
            Search poker educational videos for relevant content.

            Args:
                query: Search query (poker concepts, strategies, terms)
                top_k: Number of results to return

            Returns:
                Formatted search results with video excerpts
            """
            # Create embedding for query
            response = ctx.deps.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=query
            )
            query_embedding = response.data[0].embedding

            # Hybrid search: semantic + taxonomy-based title matching
            # Expand query using poker taxonomy (RFI -> "raise first in", etc.)
            taxonomy = get_taxonomy()
            expanded_terms = taxonomy.expand_query(query)

            # Build title match condition for all expanded terms
            title_conditions = " OR ".join(
                ["LOWER(v.title) LIKE LOWER(%s)"] * len(expanded_terms)
            )
            title_patterns = [f"%{term}%" for term in expanded_terms]

            # Note: <=> returns cosine distance [0,2], we convert to similarity [0,1]
            with ctx.deps.db_connection.cursor() as cur:
                sql = f"""
                    SELECT
                        t.text,
                        v.title,
                        v.url,
                        t.timestamp,
                        v.category,
                        GREATEST(0, LEAST(1, 1 - (t.embedding <=> %s::vector))) +
                        CASE WHEN {title_conditions} THEN 0.3 ELSE 0 END as similarity
                    FROM transcripts t
                    JOIN videos v ON t.video_id = v.id
                    WHERE t.embedding IS NOT NULL
                    ORDER BY similarity DESC
                    LIMIT %s
                """
                params = [query_embedding] + title_patterns + [top_k]
                cur.execute(sql, params)

                results = cur.fetchall()

            if not results:
                return "No relevant videos found for this query."

            # Format results
            formatted = []
            for i, (text, title, url, timestamp, category, similarity) in enumerate(results):
                formatted.append(
                    f"[{i+1}] {title} ({category})\n"
                    f"    URL: {url}\n"
                    f"    Timestamp: {timestamp}, Relevance: {similarity:.2f}\n"
                    f"    Transcript: \"{text}\""
                )

            return "\n\n".join(formatted)

        @agent.tool
        async def get_conversation_context(
            ctx: RunContext[RAGDependencies]
        ) -> str:
            """
            Get recent conversation history for context.

            Returns:
                Recent conversation messages
            """
            if not ctx.deps.conversation_history:
                return "No previous conversation."

            recent = ctx.deps.conversation_history[-6:]  # Last 3 exchanges
            return "\n".join([
                f"{msg.role}: {msg.content}"
                for msg in recent
            ])

        return agent

    def _translate_query(self, query: str) -> TranslatedQuery:
        """
        Detect language and translate to English if needed.
        Uses OpenAI for translation.
        """
        # Quick check: if all ASCII, likely English
        if query.isascii():
            return TranslatedQuery(
                original=query,
                translated=query,
                source_language="en"
            )

        # Use OpenAI for language detection and translation
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Fast and cheap for translation
            messages=[
                {
                    "role": "system",
                    "content": """You are a translator. Detect the language and translate to English.
Return JSON format: {"source_language": "xx", "translated": "english text"}
If already English, return the same text. Keep poker terminology accurate."""
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        result = json.loads(response.choices[0].message.content)

        return TranslatedQuery(
            original=query,
            translated=result.get("translated", query),
            source_language=result.get("source_language", "unknown")
        )

    def _get_system_prompt(self) -> str:
        """Get system prompt for poker domain"""
        return """You are an expert poker coach assistant. You help players find and understand poker concepts from educational videos.

Your capabilities:
1. Search poker educational videos using the search_videos tool
2. Remember conversation context using get_conversation_context tool

CRITICAL RULES:
- Base your answer ONLY on video transcripts - don't add external knowledge
- If transcripts don't contain the answer, say "I couldn't find this in the videos"
- NEVER repeat or quote the transcript text verbatim in your answer

Guidelines:
- Always search videos before answering poker questions
- Use poker terminology accurately
- Videos cover both PLO4 (4-card) and PLO5 (5-card) Omaha

Response format:
- Give a SHORT summary (2-3 sentences) of what the videos cover on this topic
- Example: "Found 3 videos about RFI strategy. They cover optimal raise sizing, position-based ranges, and practice methods."
- Do NOT quote transcripts - the sources section will show the details
- Let the user explore the video links for full content
- Set confidence based on how relevant the found videos are"""

    async def chat(self, question: str) -> SearchResult:
        """
        Ask a question with conversational memory

        Args:
            question: User question

        Returns:
            SearchResult with answer, sources, and confidence
        """
        # Translate query if not English
        translated = self._translate_query(question)

        # Add original question to history
        self.conversation_history.append(
            ConversationMessage(role="user", content=question)
        )

        # Create dependencies
        deps = RAGDependencies(
            db_connection=self.conn,
            openai_client=self.openai_client,
            conversation_history=self.conversation_history
        )

        # Build prompt with translation info
        if translated.source_language != "en":
            agent_prompt = f"""[User asked in {translated.source_language}: "{question}"]
[Translated query for search: "{translated.translated}"]

Please search using the translated query and respond in {translated.source_language}."""
        else:
            agent_prompt = question

        # Run agent
        result = await self.agent.run(agent_prompt, deps=deps)

        # Add response to history
        self.conversation_history.append(
            ConversationMessage(role="assistant", content=result.output.answer)
        )

        return result.output

    def chat_sync(self, question: str) -> SearchResult:
        """
        Synchronous version of chat

        Args:
            question: User question

        Returns:
            SearchResult with answer, sources, and confidence
        """
        import asyncio
        return asyncio.run(self.chat(question))

    def ask(self, question: str) -> str:
        """
        Simple interface - just get the answer

        Args:
            question: User question

        Returns:
            Answer string
        """
        result = self.chat_sync(question)
        return result.answer

    def clear_memory(self) -> None:
        """Clear conversation memory"""
        self.conversation_history = []
        print("Conversation memory cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM transcripts WHERE embedding IS NOT NULL")
            chunk_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM videos")
            video_count = cur.fetchone()[0]

        return {
            "total_videos": video_count,
            "total_chunks": chunk_count,
            "model": self.model_name,
            "memory_messages": len(self.conversation_history),
            "backend": "postgresql+pgvector"
        }

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# ============================================================================
# Simple functional interface
# ============================================================================

async def search_poker_videos(
    query: str,
    model: str = "gpt-4o-mini",
    top_k: int = 5
) -> SearchResult:
    """
    Simple function to search poker videos

    Args:
        query: Search query
        model: LLM model to use
        top_k: Number of results

    Returns:
        SearchResult with answer and sources
    """
    rag = ConversationalVideoRAG(model_name=model)
    result = await rag.chat(query)
    rag.close()
    return result


__all__ = [
    'ConversationalVideoRAG',
    'SearchResult',
    'VideoSource',
    'TranslatedQuery',
    'search_poker_videos'
]
