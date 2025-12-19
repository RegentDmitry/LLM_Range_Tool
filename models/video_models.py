#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pydantic models for video transcript RAG system
"""

from typing import Optional, List
from pydantic import BaseModel, Field, computed_field


class TranscriptSegment(BaseModel):
    """Transcript segment with timestamps"""

    id: int = Field(..., description="Segment ID")
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Segment text")

    @computed_field
    @property
    def duration(self) -> float:
        """Segment duration in seconds"""
        return self.end - self.start

    @computed_field
    @property
    def timestamp(self) -> str:
        """Formatted timestamp (MM:SS)"""
        minutes = int(self.start // 60)
        seconds = int(self.start % 60)
        return f"{minutes}:{seconds:02d}"


class VideoTranscript(BaseModel):
    """Full video transcription"""

    video_id: str = Field(..., description="Video ID (e.g., YouTube ID)")
    title: str = Field(..., description="Video title")
    url: str = Field(..., description="Video URL")
    duration: float = Field(..., description="Video duration in seconds")
    language: str = Field(default="en", description="Video language")
    segments: List[TranscriptSegment] = Field(default_factory=list, description="Transcript segments")

    @computed_field
    @property
    def full_text(self) -> str:
        """Full transcript text"""
        return " ".join([seg.text for seg in self.segments])

    @computed_field
    @property
    def segment_count(self) -> int:
        """Number of segments"""
        return len(self.segments)


class VideoChunk(BaseModel):
    """
    Video chunk for RAG system
    Combines multiple segments into one semantic block
    """

    chunk_id: str = Field(..., description="Unique chunk ID")
    video_id: str = Field(..., description="Video ID")
    video_title: str = Field(..., description="Video title")
    video_url: str = Field(..., description="Video URL")

    start_time: float = Field(..., description="Chunk start time in seconds")
    end_time: float = Field(..., description="Chunk end time in seconds")
    text: str = Field(..., description="Chunk text")

    segment_ids: List[int] = Field(default_factory=list, description="Segment IDs in this chunk")

    @computed_field
    @property
    def url_with_timestamp(self) -> str:
        """Video URL with timestamp"""
        timestamp_seconds = int(self.start_time)

        # Detect URL format
        if "youtube.com" in self.video_url or "youtu.be" in self.video_url:
            separator = "&" if "?" in self.video_url else "?"
            return f"{self.video_url}{separator}t={timestamp_seconds}s"
        else:
            # For other platforms just return URL
            return self.video_url

    @computed_field
    @property
    def timestamp(self) -> str:
        """Formatted timestamp (MM:SS)"""
        minutes = int(self.start_time // 60)
        seconds = int(self.start_time % 60)
        return f"{minutes}:{seconds:02d}"

    @computed_field
    @property
    def duration(self) -> float:
        """Chunk duration in seconds"""
        return self.end_time - self.start_time


class SearchResult(BaseModel):
    """Video search result"""

    chunk: VideoChunk = Field(..., description="Found chunk")
    score: float = Field(..., description="Relevance score (0-1)")

    @computed_field
    @property
    def formatted_result(self) -> str:
        """Formatted result for display"""
        return f"""
📹 {self.chunk.video_title}
⏱️  Timestamp: {self.chunk.timestamp}
🔗 {self.chunk.url_with_timestamp}
💬 {self.chunk.text[:200]}{'...' if len(self.chunk.text) > 200 else ''}
📊 Relevance: {self.score:.2%}
"""


class VideoMetadata(BaseModel):
    """Video metadata for vector DB storage"""

    video_id: str
    video_title: str
    video_url: str
    chunk_id: str
    start_time: float
    end_time: float
    timestamp: str
    text: str
    url_with_timestamp: str


__all__ = [
    'TranscriptSegment',
    'VideoTranscript',
    'VideoChunk',
    'SearchResult',
    'VideoMetadata',
]
