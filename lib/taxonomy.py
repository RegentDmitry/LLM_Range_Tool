#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Poker Taxonomy - concept matching and query expansion
"""

import os
import yaml
from typing import List, Set, Dict, Optional
from pathlib import Path


class PokerTaxonomy:
    """
    Loads poker taxonomy and provides query expansion.
    Maps user queries to canonical terms and aliases.
    """

    def __init__(self, taxonomy_path: Optional[str] = None):
        """Load taxonomy from YAML file"""
        if taxonomy_path is None:
            # Default path: data/poker_taxonomy.yaml
            base_dir = Path(__file__).parent.parent
            taxonomy_path = base_dir / "data" / "poker_taxonomy.yaml"

        with open(taxonomy_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        self.concepts = data.get('concepts', {})

        # Build reverse lookup: alias -> concept_key
        self._alias_to_concept: Dict[str, str] = {}
        for concept_key, concept_data in self.concepts.items():
            # Add canonical name
            name = concept_data.get('name', '').lower()
            self._alias_to_concept[name] = concept_key

            # Add all aliases
            for alias in concept_data.get('aliases', []):
                self._alias_to_concept[alias.lower()] = concept_key

    def expand_query(self, query: str) -> List[str]:
        """
        Expand query with synonyms from taxonomy.

        Args:
            query: User's search query

        Returns:
            List of expanded terms to search for
        """
        query_lower = query.lower()
        expanded = set()
        expanded.add(query)  # Always include original

        # Check if query matches any alias
        for alias, concept_key in self._alias_to_concept.items():
            if alias in query_lower:
                # Found a match - add all aliases for this concept
                concept = self.concepts[concept_key]
                expanded.add(concept['name'])
                for a in concept.get('aliases', []):
                    expanded.add(a)

        return list(expanded)

    def get_search_patterns(self, query: str) -> List[str]:
        """
        Get SQL LIKE patterns for hybrid search.

        Args:
            query: User's search query

        Returns:
            List of patterns for SQL LIKE matching
        """
        expanded = self.expand_query(query)
        # Convert to SQL LIKE patterns
        return [f"%{term}%" for term in expanded]

    def find_concept(self, term: str) -> Optional[Dict]:
        """
        Find concept by any of its aliases.

        Args:
            term: Term to look up

        Returns:
            Concept dict if found, None otherwise
        """
        term_lower = term.lower()
        if term_lower in self._alias_to_concept:
            concept_key = self._alias_to_concept[term_lower]
            return self.concepts[concept_key]
        return None

    def get_related(self, term: str) -> List[str]:
        """
        Get related concepts for a term.

        Args:
            term: Term to find relations for

        Returns:
            List of related concept names
        """
        concept = self.find_concept(term)
        if concept:
            return concept.get('related', [])
        return []


# Singleton instance
_taxonomy: Optional[PokerTaxonomy] = None


def get_taxonomy() -> PokerTaxonomy:
    """Get singleton taxonomy instance"""
    global _taxonomy
    if _taxonomy is None:
        _taxonomy = PokerTaxonomy()
    return _taxonomy


def expand_query(query: str) -> List[str]:
    """Convenience function to expand query"""
    return get_taxonomy().expand_query(query)


if __name__ == "__main__":
    # Test
    tax = PokerTaxonomy()

    print("Testing taxonomy expansion:")
    print()

    test_queries = [
        "raise first in",
        "RFI",
        "3-bet strategy",
        "c-bet OOP",
        "AAxx preflop",
        "squeeze play",
    ]

    for q in test_queries:
        expanded = tax.expand_query(q)
        print(f"'{q}' -> {expanded}")
