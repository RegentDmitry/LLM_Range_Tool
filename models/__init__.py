#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Data models for video RAG and GTO preflop systems
"""

# GTO Preflop models
from .preflop_models import (
    GameType,
    GameFormat,
    StackType,
    PlayerCount,
    PreflopTags,
    PreflopTree,
    PreflopQuery,
    PreflopSearchResult,
    TreeTag,
    parse_tree_from_dynamodb,
    filter_trees_by_query,
)

# Video models (base)
from .video_models import (
    TranscriptSegment,
    VideoTranscript,
    VideoChunk,
    SearchResult,
    VideoMetadata,
)

# Video models (AssemblyAI)
from .video_models_assemblyai import (
    Speaker,
    Chapter,
    Entity,
    Topic,
    SentimentSegment,
    KeyPhrase,
    VideoTranscriptAssemblyAI,
    VideoChunkAssemblyAI,
    AssemblyAIMetadata,
)

__all__ = [
    # Preflop models
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
    # Video models (base)
    'TranscriptSegment',
    'VideoTranscript',
    'VideoChunk',
    'SearchResult',
    'VideoMetadata',
    # Video models (AssemblyAI)
    'Speaker',
    'Chapter',
    'Entity',
    'Topic',
    'SentimentSegment',
    'KeyPhrase',
    'VideoTranscriptAssemblyAI',
    'VideoChunkAssemblyAI',
    'AssemblyAIMetadata',
]
