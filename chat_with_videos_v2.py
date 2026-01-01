#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Interactive chat interface v2 - Deep Synthesis Mode
Generates comprehensive answers like NotebookLM

Usage:
    python chat_with_videos_v2.py                    # Default: gpt-4o, comprehensive mode
    python chat_with_videos_v2.py --model gpt-4o-mini
    python chat_with_videos_v2.py --model claude-sonnet-4-20250514
    python chat_with_videos_v2.py --brief            # Short answers like v1
    python chat_with_videos_v2.py --list-models      # Show available models
"""

import warnings
warnings.filterwarnings("ignore", message=".*logfire.*")

import os
import sys
import asyncio
import argparse
import textwrap
from dotenv import load_dotenv
from lib.conversational_rag_v2 import (
    ConversationalVideoRAGv2,
    SearchResult,
    list_models,
    AVAILABLE_MODELS
)

load_dotenv()


RELEVANCE_THRESHOLD = 0.50


def print_answer(result: SearchResult):
    """Print answer with markdown-aware formatting"""
    print(f"\n{'='*70}")
    print("ANSWER")
    print('='*70)
    print(result.answer)
    print(f"\n📊 Confidence: {result.confidence:.0%}")


def print_sources(result: SearchResult):
    """Print sources grouped by video"""
    if not result.sources:
        return

    best_per_video = {}
    for source in result.sources:
        url = source.url or source.video_title
        if url not in best_per_video or source.relevance > best_per_video[url].relevance:
            best_per_video[url] = source

    unique_sources = [s for s in best_per_video.values() if s.relevance >= RELEVANCE_THRESHOLD]
    unique_sources.sort(key=lambda x: x.relevance, reverse=True)

    if not unique_sources:
        print(f"\n📚 No sources above {RELEVANCE_THRESHOLD:.0%} threshold")
        return

    print(f"\n{'='*70}")
    print(f"SOURCES ({len(unique_sources)} videos)")
    print('='*70)

    for i, source in enumerate(unique_sources, 1):
        print(f"\n[{i}] {source.video_title}")
        print(f"    Timestamp: {source.timestamp} | Relevance: {source.relevance:.0%}")
        if source.url:
            print(f"    {source.url}")
        if source.text:
            wrapped = textwrap.fill(source.text, width=80, initial_indent="    > ", subsequent_indent="      ")
            print(wrapped)


async def chat_loop(rag: ConversationalVideoRAGv2):
    """Main chat loop"""
    stats = rag.get_stats()

    print(f"\n💡 Mode: {stats['synthesis_mode'].upper()}")
    print(f"   Model: {stats['model']} ({stats['provider']})")
    print(f"   Top-K: {stats['top_k']} chunks per query")
    print()
    print("Commands: 'clear' (reset memory), 'stats', 'exit'")
    print("-" * 70)

    while True:
        try:
            question = input("\n💬 You: ").strip()

            if not question:
                continue

            if question.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break

            if question.lower() == 'clear':
                rag.clear_memory()
                continue

            if question.lower() == 'stats':
                stats = rag.get_stats()
                print(f"\n📊 Stats:")
                for key, value in stats.items():
                    print(f"   {key}: {value}")
                continue

            print("\n🤔 Synthesizing comprehensive answer...", flush=True)

            result = await rag.chat(question)

            print_answer(result)
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
    parser = argparse.ArgumentParser(
        description="Poker Video Chat v2 - Deep Synthesis Mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python chat_with_videos_v2.py
    python chat_with_videos_v2.py --model gpt-4o-mini --brief
    python chat_with_videos_v2.py --model claude-sonnet-4-20250514
    python chat_with_videos_v2.py --top-k 30
        """
    )

    parser.add_argument(
        '--model', '-m',
        default='gpt-4o',
        help='LLM model to use (default: gpt-4o)'
    )
    parser.add_argument(
        '--brief', '-b',
        action='store_true',
        help='Use brief mode (like v1) instead of comprehensive synthesis'
    )
    parser.add_argument(
        '--top-k', '-k',
        type=int,
        default=20,
        help='Number of transcript chunks to retrieve (default: 20)'
    )
    parser.add_argument(
        '--list-models', '-l',
        action='store_true',
        help='List available models and exit'
    )
    parser.add_argument(
        '--no-graph',
        action='store_true',
        help='Disable Neo4j knowledge graph features'
    )

    args = parser.parse_args()

    if args.list_models:
        list_models()
        return

    print("=" * 70)
    print("🎬 Poker Video Chat v2 - Deep Synthesis Mode")
    print("=" * 70)

    # Check API keys
    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')

    if not openai_key:
        print("❌ OPENAI_API_KEY not found in .env (required for embeddings)")
        return

    model_info = AVAILABLE_MODELS.get(args.model, {})
    if model_info.get('provider') == 'anthropic' and not anthropic_key:
        print(f"❌ ANTHROPIC_API_KEY required for model {args.model}")
        return

    # Initialize
    print("\n🔄 Initializing...")

    try:
        rag = ConversationalVideoRAGv2(
            openai_api_key=openai_key,
            anthropic_api_key=anthropic_key,
            model_name=args.model,
            synthesis_mode="brief" if args.brief else "comprehensive",
            top_k=args.top_k,
            use_graph=not args.no_graph
        )
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return

    # Run chat loop
    try:
        asyncio.run(chat_loop(rag))
    finally:
        rag.close()


if __name__ == "__main__":
    main()
