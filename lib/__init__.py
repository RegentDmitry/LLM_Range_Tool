#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Library for video RAG system with Neo4j knowledge graph
+ S3/DynamoDB utilities for GTO ranges
"""

# S3/DynamoDB utilities (for GTO ranges)
from .boto3_utils import (
    list_files_in_bucket,
    download_file_from_s3,
    upload_file_to_s3,
    get_dynamodb_record,
    get_all_dynamodb_keys,
    delete_s3,
    delete_dynamodb_record,
)

# GTO Tree system
from .data_loader import TreeDataLoader
from .query_agent import TreeQueryAgent

# Video RAG system
from .video_processor_assemblyai import VideoProcessorAssemblyAI
from .conversational_rag import ConversationalVideoRAG
from .taxonomy import PokerTaxonomy, get_taxonomy
from .graph_db import PokerGraphDB, VideoNode, ConceptNode

__all__ = [
    # S3/DynamoDB
    'list_files_in_bucket',
    'download_file_from_s3',
    'upload_file_to_s3',
    'get_dynamodb_record',
    'get_all_dynamodb_keys',
    'delete_s3',
    'delete_dynamodb_record',
    # GTO Trees
    'TreeDataLoader',
    'TreeQueryAgent',
    # Video RAG
    'VideoProcessorAssemblyAI',
    'ConversationalVideoRAG',
    'PokerTaxonomy',
    'get_taxonomy',
    'PokerGraphDB',
    'VideoNode',
    'ConceptNode',
]
