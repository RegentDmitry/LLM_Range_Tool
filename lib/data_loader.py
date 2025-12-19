#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Data loader for preflop trees from local JSON files or DynamoDB
"""

import json
from pathlib import Path
from typing import List, Optional
from models.preflop_models import PreflopTree, parse_tree_from_dynamodb


class TreeDataLoader:
    """Loader for preflop tree data"""

    def __init__(self, data_dir: str = "temp"):
        """
        Initialize loader

        Args:
            data_dir: Directory with JSON files (default: temp/)
        """
        self.data_dir = Path(data_dir)
        self._plo4_trees: Optional[List[PreflopTree]] = None
        self._plo5_trees: Optional[List[PreflopTree]] = None

    def load_plo4_trees(self, force_reload: bool = False) -> List[PreflopTree]:
        """
        Load PLO4 trees from JSON file

        Args:
            force_reload: Force reload even if already cached

        Returns:
            List of PLO4 trees
        """
        if self._plo4_trees is not None and not force_reload:
            return self._plo4_trees

        json_path = self.data_dir / "preflop-tree-dev.json"

        if not json_path.exists():
            raise FileNotFoundError(f"PLO4 data file not found: {json_path}")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self._plo4_trees = [parse_tree_from_dynamodb(item) for item in data]
        print(f"✓ Loaded {len(self._plo4_trees)} PLO4 trees")

        return self._plo4_trees

    def load_plo5_trees(self, force_reload: bool = False) -> List[PreflopTree]:
        """
        Load PLO5 trees from JSON file

        Args:
            force_reload: Force reload even if already cached

        Returns:
            List of PLO5 trees
        """
        if self._plo5_trees is not None and not force_reload:
            return self._plo5_trees

        json_path = self.data_dir / "5card-preflop-tree-dev.json"

        if not json_path.exists():
            raise FileNotFoundError(f"PLO5 data file not found: {json_path}")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self._plo5_trees = [parse_tree_from_dynamodb(item) for item in data]
        print(f"✓ Loaded {len(self._plo5_trees)} PLO5 trees")

        return self._plo5_trees

    def load_all_trees(self, force_reload: bool = False) -> List[PreflopTree]:
        """
        Load all trees (PLO4 + PLO5)

        Args:
            force_reload: Force reload even if already cached

        Returns:
            Combined list of all trees
        """
        plo4 = self.load_plo4_trees(force_reload)
        plo5 = self.load_plo5_trees(force_reload)

        all_trees = plo4 + plo5
        print(f"✓ Total trees loaded: {len(all_trees)} ({len(plo4)} PLO4 + {len(plo5)} PLO5)")

        return all_trees

    def get_tree_by_key(self, tree_key: str) -> Optional[PreflopTree]:
        """
        Find tree by exact tree_key

        Args:
            tree_key: Tree key to search for

        Returns:
            Tree if found, None otherwise
        """
        all_trees = self.load_all_trees()

        for tree in all_trees:
            if tree.tree_key == tree_key:
                return tree

        return None

    def get_stats(self) -> dict:
        """
        Get statistics about loaded trees

        Returns:
            Dictionary with statistics
        """
        all_trees = self.load_all_trees()

        stats = {
            'total': len(all_trees),
            'plo4': len([t for t in all_trees if t.game_type == 'plo4']),
            'plo5': len([t for t in all_trees if t.game_type == 'plo5']),
            'cash': len([t for t in all_trees if t.game_format == 'Cash']),
            'mtt': len([t for t in all_trees if t.game_format == 'MTT']),
            'icm': len([t for t in all_trees if t.is_icm]),
            'exploitative': len([t for t in all_trees if t.is_exploitative]),
            'with_ante': len([t for t in all_trees if t.ante and t.ante > 0]),
            'with_straddle': len([t for t in all_trees if t.straddle and t.straddle > 0]),
        }

        # Player count distribution
        player_counts = {}
        for tree in all_trees:
            count = tree.number_of_players
            player_counts[count] = player_counts.get(count, 0) + 1
        stats['by_players'] = player_counts

        # Stack size ranges
        stack_ranges = {
            '0-20bb': 0,
            '20-50bb': 0,
            '50-100bb': 0,
            '100-200bb': 0,
            '200+bb': 0,
        }
        for tree in all_trees:
            stack = float(tree.stack_size)
            if stack < 20:
                stack_ranges['0-20bb'] += 1
            elif stack < 50:
                stack_ranges['20-50bb'] += 1
            elif stack < 100:
                stack_ranges['50-100bb'] += 1
            elif stack < 200:
                stack_ranges['100-200bb'] += 1
            else:
                stack_ranges['200+bb'] += 1
        stats['by_stack'] = stack_ranges

        return stats


__all__ = ['TreeDataLoader']
