#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extended Pydantic models for AssemblyAI video transcript system
Supports advanced features: chapters, entities, topics, sentiment, speaker diarization
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, computed_field
from models.video_models import TranscriptSegment, VideoTranscript, VideoChunk


class Speaker(BaseModel):
    """Speaker information from speaker diarization"""

    speaker: str = Field(..., description="Speaker label (A, B, C, etc.)")
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Speaker's text")
    confidence: float = Field(..., description="Confidence score (0-1)")


class Chapter(BaseModel):
    """Auto-generated chapter from AssemblyAI"""

    chapter_id: int = Field(..., description="Chapter ID")
    start: float = Field(..., description="Chapter start time in seconds")
    end: float = Field(..., description="Chapter end time in seconds")
    headline: str = Field(..., description="Chapter headline/title")
    summary: str = Field(..., description="Chapter summary")
    gist: str = Field(..., description="Chapter gist (1-2 words)")

    @computed_field
    @property
    def duration(self) -> float:
        """Chapter duration in seconds"""
        return self.end - self.start

    @computed_field
    @property
    def timestamp(self) -> str:
        """Formatted timestamp (MM:SS)"""
        minutes = int(self.start // 60)
        seconds = int(self.start % 60)
        return f"{minutes}:{seconds:02d}"


class Entity(BaseModel):
    """Named entity from entity detection"""

    entity_type: str = Field(..., description="Entity type (person, location, organization, etc.)")
    text: str = Field(..., description="Entity text")
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")

    @computed_field
    @property
    def timestamp(self) -> str:
        """Formatted timestamp (MM:SS)"""
        minutes = int(self.start // 60)
        seconds = int(self.start % 60)
        return f"{minutes}:{seconds:02d}"


class Topic(BaseModel):
    """Topic/category from topic detection (IAB categories)"""

    topic: str = Field(..., description="Topic name")
    relevance: float = Field(..., description="Relevance score (0-1)")

    @computed_field
    @property
    def relevance_percent(self) -> str:
        """Formatted relevance percentage"""
        return f"{self.relevance:.1%}"


class SentimentSegment(BaseModel):
    """Sentiment analysis for a segment"""

    text: str = Field(..., description="Segment text")
    sentiment: str = Field(..., description="Sentiment (POSITIVE, NEGATIVE, NEUTRAL)")
    confidence: float = Field(..., description="Confidence score (0-1)")
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    speaker: Optional[str] = Field(None, description="Speaker label if available")

    @computed_field
    @property
    def timestamp(self) -> str:
        """Formatted timestamp (MM:SS)"""
        minutes = int(self.start // 60)
        seconds = int(self.start % 60)
        return f"{minutes}:{seconds:02d}"

    @computed_field
    @property
    def sentiment_emoji(self) -> str:
        """Emoji for sentiment"""
        return {
            "POSITIVE": "😊",
            "NEGATIVE": "😞",
            "NEUTRAL": "😐"
        }.get(self.sentiment, "❓")


class KeyPhrase(BaseModel):
    """Key phrase/highlight from auto highlights"""

    text: str = Field(..., description="Key phrase text")
    rank: float = Field(..., description="Importance rank (0-1)")
    count: int = Field(..., description="Number of occurrences")
    timestamps: List[float] = Field(default_factory=list, description="Timestamps where phrase appears")

    @computed_field
    @property
    def rank_percent(self) -> str:
        """Formatted rank percentage"""
        return f"{self.rank:.1%}"


class VideoTranscriptAssemblyAI(VideoTranscript):
    """
    Extended video transcript with AssemblyAI features
    Inherits from VideoTranscript and adds advanced features
    """

    # Advanced features
    chapters: List[Chapter] = Field(default_factory=list, description="Auto-generated chapters")
    entities: List[Entity] = Field(default_factory=list, description="Named entities")
    topics: List[Topic] = Field(default_factory=list, description="Detected topics")
    sentiment_segments: List[SentimentSegment] = Field(default_factory=list, description="Sentiment analysis")
    speakers: List[Speaker] = Field(default_factory=list, description="Speaker diarization")
    key_phrases: List[KeyPhrase] = Field(default_factory=list, description="Key phrases/highlights")

    # AssemblyAI metadata
    audio_duration: Optional[float] = Field(None, description="Audio duration from AssemblyAI")
    confidence: Optional[float] = Field(None, description="Overall transcription confidence")
    words_count: Optional[int] = Field(None, description="Total word count")

    @computed_field
    @property
    def chapter_count(self) -> int:
        """Number of chapters"""
        return len(self.chapters)

    @computed_field
    @property
    def entity_count(self) -> int:
        """Number of entities"""
        return len(self.entities)

    @computed_field
    @property
    def speaker_count(self) -> int:
        """Number of unique speakers"""
        return len(set(s.speaker for s in self.speakers))

    @computed_field
    @property
    def top_topics(self) -> List[str]:
        """Top 5 topics by relevance"""
        sorted_topics = sorted(self.topics, key=lambda t: t.relevance, reverse=True)
        return [t.topic for t in sorted_topics[:5]]

    @computed_field
    @property
    def sentiment_summary(self) -> Dict[str, int]:
        """Sentiment distribution"""
        summary = {"POSITIVE": 0, "NEGATIVE": 0, "NEUTRAL": 0}
        for seg in self.sentiment_segments:
            summary[seg.sentiment] = summary.get(seg.sentiment, 0) + 1
        return summary


class VideoChunkAssemblyAI(VideoChunk):
    """
    Extended video chunk with AssemblyAI metadata
    Inherits from VideoChunk and adds advanced features
    """

    # Chapter information
    chapter_id: Optional[int] = Field(None, description="Chapter ID if chunk belongs to a chapter")
    chapter_headline: Optional[str] = Field(None, description="Chapter headline")

    # Entities in this chunk
    entities: List[str] = Field(default_factory=list, description="Entity texts in this chunk")
    entity_types: List[str] = Field(default_factory=list, description="Entity types in this chunk")

    # Topics in this chunk
    topics: List[str] = Field(default_factory=list, description="Topics relevant to this chunk")

    # Sentiment
    dominant_sentiment: Optional[str] = Field(None, description="Dominant sentiment (POSITIVE/NEGATIVE/NEUTRAL)")
    sentiment_confidence: Optional[float] = Field(None, description="Sentiment confidence (0-1)")

    # Speaker
    speaker: Optional[str] = Field(None, description="Speaker label if applicable")

    @computed_field
    @property
    def has_chapter(self) -> bool:
        """Whether chunk belongs to a chapter"""
        return self.chapter_id is not None

    @computed_field
    @property
    def entity_summary(self) -> str:
        """Summary of entities in chunk"""
        if not self.entities:
            return "No entities"
        return ", ".join(self.entities[:3]) + (f" (+{len(self.entities)-3} more)" if len(self.entities) > 3 else "")


class AssemblyAIMetadata(BaseModel):
    """Metadata for AssemblyAI processing"""

    video_id: str
    title: str
    url: str

    # Processing info
    duration: float
    language: str
    confidence: float

    # Feature counts
    segment_count: int
    chapter_count: int
    entity_count: int
    speaker_count: int
    chunk_count: int

    # Topics
    top_topics: List[str]

    # Sentiment
    sentiment_summary: Dict[str, int]

    # Processing time
    created_at: str


__all__ = [
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
