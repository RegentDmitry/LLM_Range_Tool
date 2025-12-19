#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pydantic AI agent for parsing user questions into structured queries
"""

from typing import List
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from models.preflop_models import (
    PreflopQuery,
    PreflopTree,
    PreflopSearchResult,
    filter_trees_by_query,
)


# System prompt for the agent
SYSTEM_PROMPT = """You are a poker GTO expert assistant specializing in PLO4 and PLO5.

Your task is to parse user questions about poker situations into structured queries.

Extract the following parameters from user questions:
- game_type: "plo4" or "plo5" (default: plo4)
- game_format: "Cash" or "MTT"
- number_of_players: 2-8 (common: 2=Heads-Up, 6=6-Max, 8=8-Max)
- stack_size: in big blinds (bb)
- category: tree category if mentioned
- poker_room: if specific room mentioned (GGPoker, PokerStars, etc.)
- with_ante: true if ante is mentioned
- with_straddle: true if straddle is mentioned
- icm_only: true if ICM or tournament bubble mentioned
- exploitative_only: true if exploitative strategy mentioned
- query_text: any additional free text

Examples:
- "6-max cash 100bb PLO4" → number_of_players=6, game_format="Cash", stack_size=100, game_type="plo4"
- "heads up MTT with ante" → number_of_players=2, game_format="MTT", with_ante=true
- "ICM situation 6-max" → icm_only=true, number_of_players=6
- "exploitative tree for aggressive opponent" → exploitative_only=true

Be smart about natural language:
- "стокс 100бб" = stack_size=100
- "шестимакс" or "6макс" = number_of_players=6
- "кэш" = game_format="Cash"
- "турнир" or "мтт" = game_format="MTT"
- "хуху" or "heads-up" = number_of_players=2

Return a PreflopQuery object with extracted parameters.
"""


class TreeQueryAgent:
    """Agent for parsing user questions and searching trees"""

    def __init__(self, model: str = 'openai:gpt-4o-mini'):
        """
        Initialize agent

        Args:
            model: Model to use (default: gpt-4o-mini for speed/cost)
                  Options: 'openai:gpt-4o', 'openai:gpt-4o-mini', 'anthropic:claude-3-5-sonnet-20241022'
        """
        # Pydantic AI with output_type for structured output
        self.agent = Agent(
            model,
            output_type=PreflopQuery,
            system_prompt=SYSTEM_PROMPT
        )

    async def parse_question(self, question: str) -> PreflopQuery:
        """
        Parse user question into structured query

        Args:
            question: User question in natural language

        Returns:
            Structured PreflopQuery object
        """
        # Run agent and get structured output
        result = await self.agent.run(question)

        # Pydantic AI returns structured data in result.output
        return result.output

    async def search_trees(
        self,
        question: str,
        trees: List[PreflopTree]
    ) -> List[PreflopSearchResult]:
        """
        Parse question and search for matching trees

        Args:
            question: User question in natural language
            trees: List of all available trees

        Returns:
            List of search results with relevance scores
        """
        # Parse question into query
        query = await self.parse_question(question)

        # Filter trees
        matching_trees = filter_trees_by_query(trees, query)

        # Convert to search results
        results = [
            PreflopSearchResult.from_tree(tree, score=1.0)
            for tree in matching_trees
        ]

        return results

    def format_results(self, results: List[PreflopSearchResult]) -> str:
        """
        Format search results as readable text

        Args:
            results: List of search results

        Returns:
            Formatted string
        """
        if not results:
            return "❌ No matching trees found"

        output = [f"✓ Found {len(results)} matching tree(s):\n"]

        for i, result in enumerate(results, 1):
            tree = result.tree
            output.append(f"{i}. {tree.display_name}")
            output.append(f"   Category: {tree.category}")
            output.append(f"   Profile: {tree.profile}")
            output.append(f"   Game: {tree.game_type.upper() if hasattr(tree.game_type, 'upper') else tree.game_type} | Format: {tree.game_format}")

            if tree.ante:
                output.append(f"   Ante: {tree.ante}bb")
            if tree.is_icm:
                output.append(f"   ICM: Yes")
            if tree.is_exploitative:
                output.append(f"   Exploitative: Yes")

            output.append(f"   📄 Tree JSON: {result.s3_tree_url}")
            output.append(f"   📊 Ranges: {result.s3_ranges_url}")
            output.append("")

        return "\n".join(output)


__all__ = ['TreeQueryAgent']
