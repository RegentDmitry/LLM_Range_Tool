#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple usage example - demonstrates basic workflow
"""

import asyncio
from dotenv import load_dotenv
from lib import TreeDataLoader, TreeQueryAgent

# Load environment variables from .env file
load_dotenv()


async def main():
    """Simple example"""

    # 1. Load data
    print("Loading data...")
    loader = TreeDataLoader()
    trees = loader.load_all_trees()
    print()

    # 2. Create agent
    agent = TreeQueryAgent(model='openai:gpt-4o-mini')

    # 3. Ask a question
    question = "Find trees for 6-max cash PLO4 at 100bb"
    print(f"Question: {question}\n")

    # 4. Search
    results = await agent.search_trees(question, trees)

    # 5. Show results
    print(agent.format_results(results))


if __name__ == "__main__":
    asyncio.run(main())
