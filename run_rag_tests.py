#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Automated test script for RAG system - runs predefined test queries
For interactive mode, use run_rag_manual.py
"""

import asyncio
import os
from dotenv import load_dotenv
from lib import TreeDataLoader, TreeQueryAgent

# Load environment variables from .env file
load_dotenv()


async def main():
    """Main test function"""

    print("=" * 60)
    print("PLO4/PLO5 GTO Tree Finder - Automated Tests")
    print("=" * 60)
    print()

    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  Warning: OPENAI_API_KEY not found in environment")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        print()

    # Load data
    print("📂 Loading tree data...")
    loader = TreeDataLoader()
    trees = loader.load_all_trees()
    print()

    # Show stats
    print("📊 Database Statistics:")
    stats = loader.get_stats()
    print(f"   Total trees: {stats['total']}")
    print(f"   PLO4: {stats['plo4']} | PLO5: {stats['plo5']}")
    print(f"   Cash: {stats['cash']} | MTT: {stats['mtt']}")
    print(f"   ICM: {stats['icm']} | Exploitative: {stats['exploitative']}")
    print(f"   With ante: {stats['with_ante']} | With straddle: {stats['with_straddle']}")
    print()
    print(f"   By players: {stats['by_players']}")
    print()

    # Initialize agent
    print("🤖 Initializing AI agent...")
    # Using gpt-4o-mini for speed and lower cost
    agent = TreeQueryAgent(model='openai:gpt-4o-mini')
    print("✓ Agent ready")
    print()

    # Test queries
    test_questions = [
        "Find trees for 6-max cash PLO4 at 100bb",
        "heads up MTT with ante",
        "ICM situation 6-max",
        "exploitative tree",
        "найди дерево для 6-макс кэш на стеках 100бб",  # Russian test
    ]

    print("=" * 60)
    print("Running Test Queries")
    print("=" * 60)
    print()

    for i, question in enumerate(test_questions, 1):
        print(f"[Query {i}] {question}")
        print("-" * 60)

        try:
            # Search for trees
            results = await agent.search_trees(question, trees)

            # Format and print results
            formatted = agent.format_results(results)
            print(formatted)

        except Exception as e:
            print(f"❌ Error: {e}")
            print()

        print()

    # Done
    print("=" * 60)
    print("✓ Tests completed!")
    print("=" * 60)
    print()
    print("For interactive mode, run: python run_rag_manual.py")


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
