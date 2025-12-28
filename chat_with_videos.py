#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Interactive chat interface for conversational video search
Using Pydantic AI (production-ready, type-safe)
"""

import warnings
warnings.filterwarnings("ignore", message=".*logfire.*")

import os
import asyncio
import textwrap
from dotenv import load_dotenv
from lib.conversational_rag import ConversationalVideoRAG, SearchResult

load_dotenv()


RELEVANCE_THRESHOLD = 0.50  # Minimum relevance to show (50%)


def print_sources(result: SearchResult):
    """Print source documents nicely, grouped by video (best result only)"""
    if not result.sources:
        return

    # Group by video URL, keep only the most relevant per video
    best_per_video = {}
    for source in result.sources:
        url = source.url or source.video_title
        if url not in best_per_video or source.relevance > best_per_video[url].relevance:
            best_per_video[url] = source

    # Filter by threshold and sort
    unique_sources = [s for s in best_per_video.values() if s.relevance >= RELEVANCE_THRESHOLD]
    unique_sources.sort(key=lambda x: x.relevance, reverse=True)

    if not unique_sources:
        print(f"\n📚 No sources above {RELEVANCE_THRESHOLD:.0%} relevance threshold")
        return

    print(f"\n📚 Sources ({len(unique_sources)} videos):")
    for i, source in enumerate(unique_sources, 1):
        print(f"\n  [{i}] {source.video_title}")
        print(f"      ⏱️  Best match: {source.timestamp}")
        print(f"      📊 Relevance: {source.relevance:.0%}")
        if source.url:
            print(f"      🔗 {source.url}")
        if source.text:
            wrapped = textwrap.fill(source.text, width=85, initial_indent="      💬 \"", subsequent_indent="          ")
            print(f"{wrapped}\"")


async def chat_loop(rag: ConversationalVideoRAG):
    """Main chat loop"""
    print("\n💡 Tips:")
    print("   • Ask in any language (auto-translation to English for search)")
    print("   • Example: 'как играть AAxx на префлопе?'")
    print("   • Ask 'what should I learn before X?' for learning paths")
    print("   • Ask 'similar videos to X' for recommendations")
    print("   • Type 'clear' to reset, 'stats' for info, 'exit' to quit")
    print()
    print("-" * 70)

    while True:
        try:
            # Get user input
            question = input("\n💬 You: ").strip()

            if not question:
                continue

            # Commands
            if question.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break

            if question.lower() == 'clear':
                rag.clear_memory()
                continue

            if question.lower() == 'stats':
                stats = rag.get_stats()
                print(f"\n📊 Stats:")
                print(f"   Backend: {stats['backend']}")
                print(f"   Model: {stats['model']}")
                print(f"   Videos: {stats['total_videos']}")
                print(f"   Chunks: {stats['total_chunks']}")
                print(f"   Messages in memory: {stats['memory_messages']}")
                print(f"   Graph: {'enabled' if stats.get('graph_enabled') else 'disabled'}")
                if stats.get('graph_enabled'):
                    print(f"   Graph concepts: {stats.get('graph_concepts', 0)}")
                    print(f"   Graph mentions: {stats.get('graph_mentions', 0)}")
                continue

            # Get answer
            print("\n🤔 Thinking...", flush=True)

            result = await rag.chat(question)

            # Print answer
            print(f"\n🤖 Assistant:")
            wrapped_answer = textwrap.fill(result.answer, width=85, initial_indent="", subsequent_indent="")
            print(wrapped_answer)
            print(f"\n📊 Confidence: {result.confidence:.0%}")

            # Print sources
            print_sources(result)

            print("\n" + "-" * 70)

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


def main():
    print("=" * 70)
    print("🎬 Poker Video Chat - Pydantic AI")
    print("=" * 70)
    print()

    # Initialize
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("❌ OPENAI_API_KEY not found in .env")
        return

    # Create conversational RAG
    print("🔄 Initializing...")
    rag = ConversationalVideoRAG(
        openai_api_key=openai_key,
        model_name="gpt-4o",
    )
    print()

    # Run chat loop
    asyncio.run(chat_loop(rag))


if __name__ == "__main__":
    main()
