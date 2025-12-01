#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pydantic models for PLO4/PLO5 preflop RAG system
"""

from typing import Optional, Dict, List, Union, Literal
from pydantic import BaseModel, Field, computed_field
from enum import Enum


# ==================== Enums ====================

class GameType(str, Enum):
    """Game type"""
    PLO4 = "plo4"
    PLO5 = "plo5"


class GameFormat(str, Enum):
    """Game format"""
    CASH = "Cash"
    MTT = "MTT"


class StackType(str, Enum):
    """Stack type"""
    SYMMETRIC = "Symmetric"
    ASYMMETRIC = "Asymmetric"


class PlayerCount(int, Enum):
    """Number of players"""
    HEADS_UP = 2
    THREE_MAX = 3
    FOUR_MAX = 4
    FIVE_MAX = 5
    SIX_MAX = 6
    SEVEN_MAX = 7
    EIGHT_MAX = 8


# ==================== Core Models ====================

class PreflopTags(BaseModel):
    """
    Tags for describing preflop situations.
    Used for semantic search and filtering.
    """
    # Core tags
    game: Optional[str] = Field(None, description="Game type (Cash/MTT)")
    type: Optional[str] = Field(None, description="Tree type (Classic, Ante & Straddle, ICM, etc.)")
    players: Optional[str] = Field(None, description="Player count (6-Max, Heads Up, etc.)")
    street: Optional[str] = Field(None, description="Street (usually Preflop)")

    # Stack parameters
    stack_size: Optional[str] = Field(None, alias="Stack Size", description="Stack size")
    stack_type: Optional[str] = Field(None, alias="Stack Type", description="Stack type (Symmetric/Asymmetric)")

    # Game parameters
    poker_room: Optional[str] = Field(None, alias="Poker Room", description="Poker room")
    stake: Optional[str] = Field(None, alias="Stake", description="Stake level")
    rake: Optional[str] = Field(None, alias="Rake", description="Rake")

    # Additional parameters
    format: Optional[str] = Field(None, alias="Format", description="Format (Ante, Straddle, etc.)")
    total_ante: Optional[str] = Field(None, alias="Total Ante", description="Total ante")
    raise_size: Optional[str] = Field(None, alias="Raise Size", description="Raise size")

    # Positions (for ICM)
    btn: Optional[str] = Field(None, alias="BTN", description="BTN stack")
    sb: Optional[str] = Field(None, alias="SB", description="SB stack")
    bb: Optional[str] = Field(None, alias="BB", description="BB stack")
    co: Optional[str] = Field(None, alias="CO", description="CO stack")
    mp: Optional[str] = Field(None, alias="MP", description="MP stack")
    ep: Optional[str] = Field(None, alias="EP", description="EP stack")
    avg: Optional[str] = Field(None, alias="AVG", description="Average stack")

    # Exploitative trees
    node_lock_scenario: Optional[str] = Field(None, alias="Node Lock Scenario", description="Node lock scenario")
    node_lock_position: Optional[str] = Field(None, alias="Node Lock Position", description="Node lock position")
    player_type: Optional[str] = Field(None, alias="Player Type", description="Player type (TP, TA, LP, LA, MA)")
    description: Optional[str] = Field(None, alias="Description", description="Detailed description")

    class Config:
        populate_by_name = True
        use_enum_values = True

    def to_search_string(self) -> str:
        """Converts tags to a string for semantic search"""
        parts = []

        # Core parameters
        if self.game:
            parts.append(f"Game: {self.game}")
        if self.type:
            parts.append(f"Type: {self.type}")
        if self.players:
            parts.append(f"Players: {self.players}")
        if self.stack_size:
            parts.append(f"Stack: {self.stack_size}bb")
        if self.stack_type:
            parts.append(f"Stack Type: {self.stack_type}")

        # Poker room and stakes
        if self.poker_room:
            parts.append(f"Room: {self.poker_room}")
        if self.stake:
            parts.append(f"Stake: {self.stake}")

        # Special formats
        if self.format:
            parts.append(f"Format: {self.format}")
        if self.total_ante:
            parts.append(f"Ante: {self.total_ante}")

        # Exploitative
        if self.description:
            parts.append(f"Description: {self.description}")
        if self.node_lock_scenario:
            parts.append(f"Scenario: {self.node_lock_scenario}")

        return " | ".join(parts)


class PreflopTree(BaseModel):
    """
    Core model of preflop tree for RAG system.
    Contains only important parameters for identifying and searching situations.
    """

    # ===== Key identification parameters (required) =====
    tree_key: str = Field(..., alias="treeKey", description="Unique tree key")
    profile: str = Field(..., description="Game profile (primary identifier)")
    category: str = Field(..., description="Tree category")
    number_of_players: int = Field(..., alias="numberOfPlayers", description="Number of players (2-8)")
    stack_size: Union[int, float, str] = Field(..., alias="stackSize", description="Stack size in BB")

    # ===== Game type (for PLO4/PLO5) =====
    game_type: GameType = Field(default=GameType.PLO4, alias="gameType", description="Game type (PLO4/PLO5)")

    # ===== Tags for semantic search =====
    tags: PreflopTags = Field(default_factory=PreflopTags, description="Tags describing the situation")

    # ===== Game parameters (important for context) =====
    ante: Optional[float] = Field(None, description="Ante size")
    straddle: Optional[int] = Field(None, description="Straddle size")

    # ===== ICM parameters (for tournaments) =====
    icm_payouts: Optional[Dict[str, int]] = Field(None, alias="icmPayouts", description="ICM payouts")
    icm_stacks: Optional[Dict[str, Union[int, float]]] = Field(None, alias="icmStacks", description="ICM stacks by position")

    class Config:
        populate_by_name = True
        use_enum_values = True

    @computed_field
    @property
    def display_name(self) -> str:
        """Human-readable name for display"""
        return f"{self.category} - {self.stack_size}bb - {self.number_of_players}p"

    @computed_field
    @property
    def game_format(self) -> str:
        """Determines game format (Cash/MTT) from tags"""
        if self.tags and self.tags.game:
            return self.tags.game
        return "Cash"  # default

    @computed_field
    @property
    def is_icm(self) -> bool:
        """Checks if tree uses ICM"""
        return self.icm_payouts is not None

    @computed_field
    @property
    def is_exploitative(self) -> bool:
        """Checks if tree is exploitative"""
        return "EXP" in self.category.upper() or (
            self.tags and self.tags.type and "Exploitative" in self.tags.type
        )

    def to_search_document(self) -> str:
        """
        Converts tree to text document for semantic search.
        This is what will be indexed in the RAG system.
        """
        # If game_type is already a string (due to use_enum_values), use as is
        gt_str = self.game_type.value if isinstance(self.game_type, GameType) else self.game_type

        parts = [
            f"Tree: {self.tree_key}",
            f"Profile: {self.profile}",
            f"Category: {self.category}",
            f"Players: {self.number_of_players}",
            f"Stack: {self.stack_size}bb",
            f"Game Type: {gt_str}",
        ]

        if self.game_format:
            parts.append(f"Format: {self.game_format}")

        if self.is_icm:
            parts.append("ICM: Yes")

        if self.ante:
            parts.append(f"Ante: {self.ante}bb")

        if self.straddle:
            parts.append(f"Straddle: {self.straddle}bb")

        # Add tags
        if self.tags:
            parts.append(self.tags.to_search_string())

        return "\n".join(parts)

    def get_s3_bucket(self) -> str:
        """
        Returns S3 bucket name for tree JSON files based on game type.
        PLO4: preflop-trees
        PLO5: plo5-preflop-trees
        """
        gt_str = self.game_type.value if isinstance(self.game_type, GameType) else self.game_type
        if gt_str == 'plo5':
            return 'plo5-preflop-trees'
        return 'preflop-trees'

    def get_s3_ranges_bucket(self) -> str:
        """
        Returns S3 bucket name for preflop ranges based on game type.
        PLO4: postflop-ranges-json
        PLO5: plo5-preflop-ranges
        """
        gt_str = self.game_type.value if isinstance(self.game_type, GameType) else self.game_type
        if gt_str == 'plo5':
            return 'plo5-preflop-ranges'
        return 'postflop-ranges-json'

    def get_s3_tree_path(self) -> str:
        """
        Generates path to JSON tree in S3 (without bucket).
        Format: {category}/{tree_key}.json.gz
        Example: PLO/PLO500_30_6.json.gz
        """
        return f"{self.category}/{self.tree_key}.json.gz"

    def get_s3_tree_url(self, region: str = "eu-central-1") -> str:
        """
        Generates full S3 URL to JSON tree.
        Format: https://{bucket}.s3.dualstack.{region}.amazonaws.com/{category}/{tree_key}.json.gz
        """
        bucket = self.get_s3_bucket()
        path = self.get_s3_tree_path()
        return f"https://{bucket}.s3.dualstack.{region}.amazonaws.com/{path}"

    def get_s3_ranges_prefix(self) -> str:
        """
        Generates prefix for preflop ranges folder in S3.
        Format: {category}/{profile}/{stack_size}/{players}/preflop/
        Example PLO4: PLO/PLO500/100/6/preflop/
        Example PLO5: PLO5-COIN/PLO5C-1000CHU/100/2/preflop/
        """
        return f"{self.category}/{self.profile}/{self.stack_size}/{self.number_of_players}/preflop/"

    def get_s3_ranges_url(self, region: str = "eu-central-1") -> str:
        """
        Generates full S3 URL to preflop ranges folder.
        Format: https://{ranges_bucket}.s3.dualstack.{region}.amazonaws.com/{category}/{profile}/{stack_size}/{players}/preflop/
        """
        bucket = self.get_s3_ranges_bucket()
        prefix = self.get_s3_ranges_prefix()
        return f"https://{bucket}.s3.dualstack.{region}.amazonaws.com/{prefix}"


# ==================== Query Models ====================

class PreflopQuery(BaseModel):
    """
    Query to RAG system for searching preflop situation.
    """

    # Core parameters (can be partial)
    game_type: Optional[GameType] = Field(None, description="Game type (PLO4/PLO5)")
    game_format: Optional[GameFormat] = Field(None, description="Format (Cash/MTT)")
    number_of_players: Optional[int] = Field(None, description="Number of players (2-8)")
    stack_size: Optional[Union[int, float, str]] = Field(None, description="Stack size in BB")

    # Additional filters
    category: Optional[str] = Field(None, description="Tree category")
    profile: Optional[str] = Field(None, description="Game profile")
    poker_room: Optional[str] = Field(None, description="Poker room")
    stake: Optional[str] = Field(None, description="Stake level")

    # Special parameters
    with_ante: Optional[bool] = Field(None, description="With ante")
    with_straddle: Optional[bool] = Field(None, description="With straddle")
    icm_only: Optional[bool] = Field(None, description="Only ICM trees")
    exploitative_only: Optional[bool] = Field(None, description="Only exploitative trees")

    # Free text query
    query_text: Optional[str] = Field(None, description="Free text query")

    # Search settings
    max_results: int = Field(10, ge=1, le=100, description="Maximum number of results")

    class Config:
        use_enum_values = True

    def to_search_string(self) -> str:
        """Converts query to string for semantic search"""
        parts = []

        if self.game_type:
            gt_str = self.game_type.value if isinstance(self.game_type, GameType) else self.game_type
            parts.append(f"Game Type: {gt_str}")

        if self.game_format:
            fmt_str = self.game_format.value if isinstance(self.game_format, GameFormat) else self.game_format
            parts.append(f"Format: {fmt_str}")

        if self.number_of_players:
            parts.append(f"Players: {self.number_of_players}")

        if self.stack_size:
            parts.append(f"Stack: {self.stack_size}bb")

        if self.category:
            parts.append(f"Category: {self.category}")

        if self.profile:
            parts.append(f"Profile: {self.profile}")

        if self.poker_room:
            parts.append(f"Room: {self.poker_room}")

        if self.stake:
            parts.append(f"Stake: {self.stake}")

        if self.with_ante:
            parts.append("With Ante")

        if self.with_straddle:
            parts.append("With Straddle")

        if self.icm_only:
            parts.append("ICM")

        if self.exploitative_only:
            parts.append("Exploitative")

        if self.query_text:
            parts.append(self.query_text)

        return " ".join(parts)


class PreflopSearchResult(BaseModel):
    """
    Preflop tree search result.
    """
    tree: PreflopTree = Field(..., description="Found tree")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")
    s3_bucket: str = Field(..., description="S3 bucket name for tree JSON")
    s3_tree_path: str = Field(..., description="Path to JSON tree in S3 (without bucket)")
    s3_tree_url: str = Field(..., description="Full S3 URL to JSON tree")
    s3_ranges_bucket: str = Field(..., description="S3 bucket name for ranges")
    s3_ranges_prefix: str = Field(..., description="Prefix for ranges folder in S3")
    s3_ranges_url: str = Field(..., description="Full S3 URL to ranges folder")

    @classmethod
    def from_tree(cls, tree: PreflopTree, score: float = 1.0) -> "PreflopSearchResult":
        """Creates search result from tree"""
        return cls(
            tree=tree,
            relevance_score=score,
            s3_bucket=tree.get_s3_bucket(),
            s3_tree_path=tree.get_s3_tree_path(),
            s3_tree_url=tree.get_s3_tree_url(),
            s3_ranges_bucket=tree.get_s3_ranges_bucket(),
            s3_ranges_prefix=tree.get_s3_ranges_prefix(),
            s3_ranges_url=tree.get_s3_ranges_url()
        )


# ==================== Tag Reference Model ====================

class TreeTag(BaseModel):
    """
    Model for tag reference from tree-tags-dev table.
    Used for validation and autocomplete.
    """
    tag_key: str = Field(..., alias="tagKey", description="Tag key")
    caption: Optional[str] = Field(None, description="Tag description")
    tooltip: Optional[List[str]] = Field(None, description="Tooltip")
    children: Optional[List[str]] = Field(None, description="Valid values")
    default: Optional[List[str]] = Field(None, description="Default values")
    order: Optional[List[str]] = Field(None, description="Display order")
    group: Optional[int] = Field(None, description="Tag group")
    hide_from_selection: Optional[bool] = Field(None, alias="hideFromSelection", description="Hide from UI")
    any: Optional[bool] = Field(None, description="'Any' flag")

    class Config:
        populate_by_name = True


# ==================== Helper Functions ====================

def parse_tree_from_dynamodb(dynamodb_item: Dict) -> PreflopTree:
    """
    Parses DynamoDB record into PreflopTree model.
    """
    # Process tags
    tags_data = dynamodb_item.get('tags', {})
    tags = PreflopTags(**tags_data)

    # Create main model
    tree_data = {
        **dynamodb_item,
        'tags': tags,
        'gameType': dynamodb_item.get('gameType', 'plo4')  # default to PLO4
    }

    return PreflopTree(**tree_data)


def filter_trees_by_query(trees: List[PreflopTree], query: PreflopQuery) -> List[PreflopTree]:
    """
    Filters trees by query (basic filtering without semantic search).
    """
    filtered = trees

    # Filter by game type
    if query.game_type:
        filtered = [t for t in filtered if t.game_type == query.game_type]

    # Filter by format
    if query.game_format:
        # If game_format is already a string, use as is
        fmt_str = query.game_format.value if isinstance(query.game_format, GameFormat) else query.game_format
        filtered = [t for t in filtered if t.game_format == fmt_str]

    # Filter by number of players
    if query.number_of_players:
        filtered = [t for t in filtered if t.number_of_players == query.number_of_players]

    # Filter by stack size
    if query.stack_size:
        stack_size_num = float(query.stack_size) if isinstance(query.stack_size, str) else query.stack_size
        filtered = [t for t in filtered if float(t.stack_size) == stack_size_num]

    # Filter by category
    if query.category:
        filtered = [t for t in filtered if query.category.lower() in t.category.lower()]

    # Filter by profile
    if query.profile:
        filtered = [t for t in filtered if query.profile.lower() in t.profile.lower()]

    # Filter by poker room
    if query.poker_room:
        filtered = [t for t in filtered if t.tags and t.tags.poker_room and
                   query.poker_room.lower() in t.tags.poker_room.lower()]

    # Filter by ante
    if query.with_ante is not None:
        if query.with_ante:
            filtered = [t for t in filtered if t.ante and t.ante > 0]
        else:
            filtered = [t for t in filtered if not t.ante or t.ante == 0]

    # Filter by straddle
    if query.with_straddle is not None:
        if query.with_straddle:
            filtered = [t for t in filtered if t.straddle and t.straddle > 0]
        else:
            filtered = [t for t in filtered if not t.straddle or t.straddle == 0]

    # Filter by ICM
    if query.icm_only:
        filtered = [t for t in filtered if t.is_icm]

    # Filter by exploitative
    if query.exploitative_only:
        filtered = [t for t in filtered if t.is_exploitative]

    return filtered[:query.max_results]


__all__ = [
    'GameType',
    'GameFormat',
    'StackType',
    'PlayerCount',
    'PreflopTags',
    'PreflopTree',
    'PreflopQuery',
    'PreflopSearchResult',
    'TreeTag',
    'parse_tree_from_dynamodb',
    'filter_trees_by_query',
]
