#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Interactive manual mode for RAG system - ask your own questions
"""

import asyncio
import os
from dotenv import load_dotenv
from lib import TreeDataLoader, TreeQueryAgent

# Load environment variables from .env file
load_dotenv()


async def main():
    """Main interactive function"""

    print("=" * 60)
    print("PLO4/PLO5 GTO Tree Finder - Interactive Mode")
    print("=" * 60)
    print()

    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  Warning: OPENAI_API_KEY not found in environment")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        print()
        return

    # Load data
    print("📂 Loading tree data...")
    loader = TreeDataLoader()
    trees = loader.load_all_trees()
    print()

    # Show quick stats
    stats = loader.get_stats()
    print(f"📊 Loaded {stats['total']} trees ({stats['plo4']} PLO4 + {stats['plo5']} PLO5)")
    print()

    # Initialize agent
    print("🤖 Initializing AI agent...")
    agent = TreeQueryAgent(model='openai:gpt-4o-mini')
    print("✓ Agent ready")
    print()

    # Interactive mode
    print("=" * 60)
    print("Ask your questions about GTO trees!")
    print("=" * 60)
    print()
    print("Examples:")
    print('  - "Find trees for 6-max cash PLO4 at 100bb"')
    print('  - "heads up MTT with ante"')
    print('  - "ICM situation 6-max"')
    print('  - "найди дерево для 6-макс кэш на стеках 100бб"')
    print()
    print("Type 'quit' or 'exit' to stop, Ctrl+C to abort")
    print("=" * 60)
    print()

    while True:
        try:
            question = input("Your question: ").strip()

            if not question:
                continue

            if question.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break

            print()
            print("🔍 Searching...")

            # Search
            results = await agent.search_trees(question, trees)
            formatted = agent.format_results(results)
            print()
            print(formatted)
            print()

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print()


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
