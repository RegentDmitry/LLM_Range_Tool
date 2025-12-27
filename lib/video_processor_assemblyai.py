#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Video processor for AssemblyAI with advanced features
Supports: chapters, entities, topics, sentiment, speaker diarization
"""

import os
import json
import re
import time
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime
import assemblyai as aai
from tqdm import tqdm

from models.video_models_assemblyai import (
    VideoTranscriptAssemblyAI,
    VideoChunkAssemblyAI,
    Chapter,
    Entity,
    Topic,
    SentimentSegment,
    Speaker,
    KeyPhrase,
    AssemblyAIMetadata
)
from models.video_models import TranscriptSegment


class VideoProcessorAssemblyAI:
    """Processor for video transcription using AssemblyAI with advanced features"""

    def __init__(self, assemblyai_api_key: Optional[str] = None):
        """
        Initialize processor

        Args:
            assemblyai_api_key: AssemblyAI API key (if not provided, reads from env variable)
        """
        api_key = assemblyai_api_key or os.getenv('ASSEMBLYAI_API_KEY')
        if not api_key:
            raise ValueError("AssemblyAI API key not found. Set ASSEMBLYAI_API_KEY env variable or pass it directly.")

        # Set API key globally
        aai.settings.api_key = api_key
        self.transcriber = aai.Transcriber()

    @staticmethod
    def _convert_timestamp(timestamp) -> float:
        """
        Convert AssemblyAI Timestamp object to seconds

        Args:
            timestamp: Timestamp from AssemblyAI (can be int, float, or Timestamp object)

        Returns:
            Time in seconds as float
        """
        if isinstance(timestamp, (int, float)):
            # Already a number, convert from ms to seconds
            return timestamp / 1000.0

        # Check for common timestamp attributes (value, milliseconds, etc.)
        for attr in ['value', 'milliseconds', 'ms', 'total_milliseconds']:
            if hasattr(timestamp, attr):
                val = getattr(timestamp, attr)
                if isinstance(val, (int, float)):
                    return val / 1000.0

        # Try to get numeric value from Timestamp object
        # AssemblyAI Timestamp objects have numeric value that can be extracted
        try:
            # Method 1: Try __int__() magic method
            if hasattr(timestamp, '__int__'):
                return int(timestamp) / 1000.0
        except (TypeError, ValueError):
            pass

        try:
            # Method 2: Try __float__() magic method
            if hasattr(timestamp, '__float__'):
                return float(timestamp) / 1000.0
        except (TypeError, ValueError):
            pass

        # Method 3: Parse from string representation (fallback)
        # String format might be like "start=8440 end=9520" or just "8440"
        str_repr = str(timestamp)

        # If it contains "start=" or "end=", extract the number
        if 'start=' in str_repr:
            # Extract first number after "start="
            match = re.search(r'start=(\d+)', str_repr)
            if match:
                return int(match.group(1)) / 1000.0

        # Try to parse as plain number
        try:
            return float(str_repr) / 1000.0
        except ValueError:
            raise ValueError(f"Cannot convert timestamp to float: {str_repr}")

    def transcribe_video(
        self,
        video_path: str,
        video_id: str,
        title: str,
        url: str,
        language: str = "en",
        enable_chapters: bool = True,
        enable_entities: bool = True,
        enable_topics: bool = True,
        enable_sentiment: bool = True,
        enable_speakers: bool = True,
        enable_highlights: bool = True
    ) -> VideoTranscriptAssemblyAI:
        """
        Transcribe video using AssemblyAI with advanced features

        Args:
            video_path: Path to video file
            video_id: Unique video ID
            title: Video title
            url: Video URL
            language: Video language (default "en")
            enable_chapters: Enable auto chapters
            enable_entities: Enable entity detection
            enable_topics: Enable topic detection (IAB categories)
            enable_sentiment: Enable sentiment analysis
            enable_speakers: Enable speaker diarization
            enable_highlights: Enable auto highlights (key phrases)

        Returns:
            VideoTranscriptAssemblyAI with all advanced features
        """
        print(f"🎬 Transcribing video with AssemblyAI: {title}")
        print(f"   File: {video_path}")
        print(f"   Features enabled:")
        if enable_chapters:
            print(f"      ✓ Auto Chapters")
        if enable_entities:
            print(f"      ✓ Entity Detection")
        if enable_topics:
            print(f"      ✓ Topic Detection")
        if enable_sentiment:
            print(f"      ✓ Sentiment Analysis")
        if enable_speakers:
            print(f"      ✓ Speaker Diarization")
        if enable_highlights:
            print(f"      ✓ Key Phrases")
        print()

        # Check file exists
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Configure transcription
        config = aai.TranscriptionConfig(
            language_code=language,
            speaker_labels=enable_speakers,
            auto_chapters=enable_chapters,
            entity_detection=enable_entities,
            iab_categories=enable_topics,
            sentiment_analysis=enable_sentiment,
            auto_highlights=enable_highlights
        )

        # Start transcription
        print("📤 Uploading file to AssemblyAI...")
        print("⏳ Processing... (this may take a few minutes)")
        print()

        transcript = self.transcriber.transcribe(video_path, config=config)

        # Check for errors
        if transcript.status == aai.TranscriptStatus.error:
            raise Exception(f"Transcription failed: {transcript.error}")

        print("✓ Transcription completed!")
        print()

        # Parse segments
        segments = []
        for i, word_data in enumerate(transcript.words):
            segment = TranscriptSegment(
                id=i,
                start=self._convert_timestamp(word_data.start),
                end=self._convert_timestamp(word_data.end),
                text=word_data.text
            )
            segments.append(segment)

        # Merge word-level segments into sentence-level segments
        merged_segments = self._merge_segments(segments)

        # Parse chapters
        chapters = []
        if enable_chapters and transcript.chapters:
            for i, chapter in enumerate(transcript.chapters):
                chapters.append(Chapter(
                    chapter_id=i,
                    start=self._convert_timestamp(chapter.start),
                    end=self._convert_timestamp(chapter.end),
                    headline=chapter.headline,
                    summary=chapter.summary,
                    gist=chapter.gist
                ))

        # Parse entities
        entities = []
        if enable_entities and transcript.entities:
            for entity in transcript.entities:
                entities.append(Entity(
                    entity_type=entity.entity_type,
                    text=entity.text,
                    start=self._convert_timestamp(entity.start),
                    end=self._convert_timestamp(entity.end)
                ))

        # Parse topics (IAB categories)
        topics = []
        if enable_topics and transcript.iab_categories:
            topic_dict = transcript.iab_categories.summary
            for topic_name, relevance in topic_dict.items():
                topics.append(Topic(
                    topic=topic_name,
                    relevance=relevance
                ))

        # Parse sentiment
        sentiment_segments = []
        if enable_sentiment and transcript.sentiment_analysis:
            for sent in transcript.sentiment_analysis:
                sentiment_segments.append(SentimentSegment(
                    text=sent.text,
                    sentiment=sent.sentiment,
                    confidence=sent.confidence,
                    start=self._convert_timestamp(sent.start),
                    end=self._convert_timestamp(sent.end),
                    speaker=sent.speaker if hasattr(sent, 'speaker') else None
                ))

        # Parse speakers
        speakers = []
        if enable_speakers and transcript.utterances:
            for utterance in transcript.utterances:
                speakers.append(Speaker(
                    speaker=utterance.speaker,
                    start=self._convert_timestamp(utterance.start),
                    end=self._convert_timestamp(utterance.end),
                    text=utterance.text,
                    confidence=utterance.confidence
                ))

        # Parse key phrases
        key_phrases = []
        if enable_highlights and transcript.auto_highlights:
            for highlight in transcript.auto_highlights.results:
                key_phrases.append(KeyPhrase(
                    text=highlight.text,
                    rank=highlight.rank,
                    count=highlight.count,
                    timestamps=[self._convert_timestamp(t) for t in highlight.timestamps]
                ))

        # Calculate real duration from last word timestamp (in ms)
        # Note: audio_duration from SDK is in seconds, but word timestamps are in ms
        real_duration = merged_segments[-1].end if merged_segments else float(transcript.audio_duration)

        # Create VideoTranscriptAssemblyAI
        video_transcript = VideoTranscriptAssemblyAI(
            video_id=video_id,
            title=title,
            url=url,
            duration=real_duration,
            language=language,
            segments=merged_segments,
            chapters=chapters,
            entities=entities,
            topics=topics,
            sentiment_segments=sentiment_segments,
            speakers=speakers,
            key_phrases=key_phrases,
            audio_duration=real_duration,
            confidence=transcript.confidence,
            words_count=len(transcript.words) if transcript.words else 0
        )

        # Print statistics
        print(f"📊 Transcription stats:")
        print(f"   Duration: {video_transcript.duration:.1f}s ({video_transcript.duration/60:.1f}min)")
        print(f"   Segments: {video_transcript.segment_count}")
        print(f"   Confidence: {video_transcript.confidence:.1%}")
        if chapters:
            print(f"   Chapters: {len(chapters)}")
        if entities:
            print(f"   Entities: {len(entities)}")
        if topics:
            print(f"   Topics: {len(topics)}")
        if sentiment_segments:
            print(f"   Sentiment segments: {len(sentiment_segments)}")
        if speakers:
            print(f"   Speakers: {video_transcript.speaker_count}")
        if key_phrases:
            print(f"   Key phrases: {len(key_phrases)}")
        print()

        return video_transcript

    def _merge_segments(self, word_segments: List[TranscriptSegment]) -> List[TranscriptSegment]:
        """
        Merge word-level segments into sentence-level segments

        Args:
            word_segments: List of word-level segments

        Returns:
            List of merged sentence-level segments
        """
        if not word_segments:
            return []

        merged = []
        current_text = []
        current_start = word_segments[0].start
        current_id = 0

        for i, seg in enumerate(word_segments):
            current_text.append(seg.text)

            # End segment on punctuation or every ~20 words
            is_punctuation = seg.text.strip().endswith(('.', '!', '?'))
            is_long_enough = len(current_text) >= 20

            if is_punctuation or is_long_enough or i == len(word_segments) - 1:
                merged.append(TranscriptSegment(
                    id=current_id,
                    start=current_start,
                    end=seg.end,
                    text=" ".join(current_text)
                ))
                current_text = []
                current_start = word_segments[i + 1].start if i + 1 < len(word_segments) else seg.end
                current_id += 1

        return merged

    def chunk_transcript(
        self,
        transcript: VideoTranscriptAssemblyAI,
        chunk_duration: float = 60.0,
        overlap: float = 10.0,
        use_chapters: bool = False
    ) -> List[VideoChunkAssemblyAI]:
        """
        Split transcript into chunks for RAG system

        Args:
            transcript: VideoTranscriptAssemblyAI to split
            chunk_duration: Chunk duration in seconds (default 60s)
            overlap: Overlap between chunks in seconds (default 5s)
            use_chapters: Use chapter boundaries for chunking (default True)

        Returns:
            List of VideoChunkAssemblyAI with enhanced metadata
        """
        print(f"📦 Creating chunks for video: {transcript.title}", flush=True)

        chunks = []

        if use_chapters and transcript.chapters:
            # Use chapter-based chunking
            print(f"   Using chapter-based chunking ({len(transcript.chapters)} chapters)", flush=True)
            chunks = self._chunk_by_chapters(transcript)
        else:
            # Use time-based chunking
            print(f"   Using time-based chunking (duration: {chunk_duration}s, overlap: {overlap}s)", flush=True)
            chunks = self._chunk_by_time(transcript, chunk_duration, overlap)

        print(f"✓ Created {len(chunks)} chunks", flush=True)
        print(flush=True)

        return chunks

    def _chunk_by_chapters(
        self,
        transcript: VideoTranscriptAssemblyAI
    ) -> List[VideoChunkAssemblyAI]:
        """Create chunks based on chapter boundaries"""
        chunks = []

        for chapter in transcript.chapters:
            # Find segments in this chapter
            chunk_segments = []
            for seg in transcript.segments:
                if seg.start >= chapter.start and seg.end <= chapter.end:
                    chunk_segments.append(seg)

            if not chunk_segments:
                continue

            # Get entities in this chapter
            chapter_entities = [
                e for e in transcript.entities
                if e.start >= chapter.start and e.end <= chapter.end
            ]

            # Get sentiment for this chapter
            chapter_sentiments = [
                s for s in transcript.sentiment_segments
                if s.start >= chapter.start and s.end <= chapter.end
            ]
            dominant_sentiment = None
            sentiment_confidence = None
            if chapter_sentiments:
                # Find most common sentiment
                sentiment_counts = {}
                for s in chapter_sentiments:
                    sentiment_counts[s.sentiment] = sentiment_counts.get(s.sentiment, 0) + 1
                dominant_sentiment = max(sentiment_counts, key=sentiment_counts.get)
                sentiment_confidence = sum(s.confidence for s in chapter_sentiments) / len(chapter_sentiments)

            # Create chunk
            # Use FULL TEXT from segments, not just summary!
            chunk_text = " ".join([s.text for s in chunk_segments])

            chunk = VideoChunkAssemblyAI(
                chunk_id=f"{transcript.video_id}_chapter_{chapter.chapter_id}",
                video_id=transcript.video_id,
                video_title=transcript.title,
                video_url=transcript.url,
                start_time=chapter.start,
                end_time=chapter.end,
                text=chunk_text,  # FULL TEXT, not summary
                segment_ids=[s.id for s in chunk_segments],
                chapter_id=chapter.chapter_id,
                chapter_headline=chapter.headline,
                entities=[e.text for e in chapter_entities],
                entity_types=[e.entity_type for e in chapter_entities],
                topics=transcript.top_topics,
                dominant_sentiment=dominant_sentiment,
                sentiment_confidence=sentiment_confidence
            )
            chunks.append(chunk)

        return chunks

    def _chunk_by_time(
        self,
        transcript: VideoTranscriptAssemblyAI,
        chunk_duration: float,
        overlap: float
    ) -> List[VideoChunkAssemblyAI]:
        """Create chunks based on time windows"""
        chunks = []
        current_start = 0.0
        chunk_counter = 0

        # Calculate total number of chunks
        total_chunks = int((transcript.duration - overlap) / (chunk_duration - overlap)) + 1

        # Progress bar
        pbar = tqdm(total=total_chunks, desc="   Creating chunks", unit="chunk", ncols=80, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{percentage:3.0f}%]')

        while current_start < transcript.duration and chunk_counter < total_chunks * 2:  # Safety limit
            chunk_end = min(current_start + chunk_duration, transcript.duration)

            # Find segments for this chunk
            chunk_segments = []
            chunk_text_parts = []

            for segment in transcript.segments:
                if segment.start < chunk_end and segment.end > current_start:
                    chunk_segments.append(segment)
                    chunk_text_parts.append(segment.text)

            if chunk_segments:
                # Get entities in this time window
                chunk_entities = [
                    e for e in transcript.entities
                    if e.start >= current_start and e.end <= chunk_end
                ]

                # Get sentiment
                chunk_sentiments = [
                    s for s in transcript.sentiment_segments
                    if s.start >= current_start and s.end <= chunk_end
                ]
                dominant_sentiment = None
                sentiment_confidence = None
                if chunk_sentiments:
                    sentiment_counts = {}
                    for s in chunk_sentiments:
                        sentiment_counts[s.sentiment] = sentiment_counts.get(s.sentiment, 0) + 1
                    dominant_sentiment = max(sentiment_counts, key=sentiment_counts.get)
                    sentiment_confidence = sum(s.confidence for s in chunk_sentiments) / len(chunk_sentiments)

                # Create chunk
                chunk = VideoChunkAssemblyAI(
                    chunk_id=f"{transcript.video_id}_chunk_{chunk_counter}",
                    video_id=transcript.video_id,
                    video_title=transcript.title,
                    video_url=transcript.url,
                    start_time=chunk_segments[0].start,
                    end_time=chunk_segments[-1].end,
                    text=" ".join(chunk_text_parts),
                    segment_ids=[seg.id for seg in chunk_segments],
                    entities=[e.text for e in chunk_entities],
                    entity_types=[e.entity_type for e in chunk_entities],
                    topics=transcript.top_topics,
                    dominant_sentiment=dominant_sentiment,
                    sentiment_confidence=sentiment_confidence
                )
                chunks.append(chunk)
                pbar.update(1)
                chunk_counter += 1

            # Move to next chunk with overlap
            next_start = chunk_end - overlap

            # Safety check: ensure we're moving forward
            if next_start <= current_start:
                print(f"\n⚠️  Warning: current_start not advancing! current={current_start:.2f}, next={next_start:.2f}", flush=True)
                break

            current_start = next_start

        pbar.close()
        return chunks

    def process_video(
        self,
        video_path: str,
        video_id: str,
        title: str,
        url: str,
        language: str = "en",
        chunk_duration: float = 60.0,
        overlap: float = 10.0,
        use_chapters: bool = False
    ) -> Tuple[VideoTranscriptAssemblyAI, List[VideoChunkAssemblyAI]]:
        """
        Full video processing: transcription + chunking with all AssemblyAI features

        Args:
            video_path: Path to video file
            video_id: Unique video ID
            title: Video title
            url: Video URL
            language: Video language
            chunk_duration: Chunk duration in seconds (if not using chapters)
            overlap: Overlap between chunks in seconds
            use_chapters: Use chapter-based chunking (default True)

        Returns:
            Tuple (VideoTranscriptAssemblyAI, List[VideoChunkAssemblyAI])
        """
        # 1. Transcription with all features
        transcript = self.transcribe_video(
            video_path=video_path,
            video_id=video_id,
            title=title,
            url=url,
            language=language
        )

        # 2. Chunking
        chunks = self.chunk_transcript(
            transcript=transcript,
            chunk_duration=chunk_duration,
            overlap=overlap,
            use_chapters=use_chapters
        )

        return transcript, chunks

    def save_transcript_to_json(
        self,
        transcript: VideoTranscriptAssemblyAI,
        chunks: List[VideoChunkAssemblyAI],
        output_dir: str = "./transcripts_assemblyai"
    ) -> Path:
        """
        Save transcript and chunks to JSON file

        Args:
            transcript: VideoTranscriptAssemblyAI to save
            chunks: List of VideoChunkAssemblyAI to save
            output_dir: Output directory (default: ./transcripts_assemblyai)

        Returns:
            Path to saved JSON file
        """
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Create filename
        json_filename = f"{transcript.video_id}_assemblyai.json"
        json_path = output_path / json_filename

        # Prepare data
        data = {
            "metadata": {
                "video_id": transcript.video_id,
                "title": transcript.title,
                "url": transcript.url,
                "duration": transcript.duration,
                "language": transcript.language,
                "segment_count": transcript.segment_count,
                "chunk_count": len(chunks),
                "confidence": transcript.confidence,
                "words_count": transcript.words_count,
                "chapter_count": transcript.chapter_count,
                "entity_count": transcript.entity_count,
                "speaker_count": transcript.speaker_count,
                "top_topics": transcript.top_topics,
                "sentiment_summary": transcript.sentiment_summary,
                "created_at": datetime.now().isoformat()
            },
            "transcript": {
                "segments": [
                    {
                        "id": seg.id,
                        "start": seg.start,
                        "end": seg.end,
                        "duration": seg.duration,
                        "timestamp": seg.timestamp,
                        "text": seg.text
                    }
                    for seg in transcript.segments
                ],
                "full_text": transcript.full_text
            },
            "chapters": [
                {
                    "chapter_id": ch.chapter_id,
                    "start": ch.start,
                    "end": ch.end,
                    "duration": ch.duration,
                    "timestamp": ch.timestamp,
                    "headline": ch.headline,
                    "summary": ch.summary,
                    "gist": ch.gist
                }
                for ch in transcript.chapters
            ],
            "entities": [
                {
                    "entity_type": e.entity_type,
                    "text": e.text,
                    "start": e.start,
                    "end": e.end,
                    "timestamp": e.timestamp
                }
                for e in transcript.entities
            ],
            "topics": [
                {
                    "topic": t.topic,
                    "relevance": t.relevance,
                    "relevance_percent": t.relevance_percent
                }
                for t in transcript.topics
            ],
            "sentiment_segments": [
                {
                    "text": s.text,
                    "sentiment": s.sentiment,
                    "confidence": s.confidence,
                    "start": s.start,
                    "end": s.end,
                    "timestamp": s.timestamp,
                    "sentiment_emoji": s.sentiment_emoji,
                    "speaker": s.speaker
                }
                for s in transcript.sentiment_segments
            ],
            "speakers": [
                {
                    "speaker": sp.speaker,
                    "start": sp.start,
                    "end": sp.end,
                    "text": sp.text,
                    "confidence": sp.confidence
                }
                for sp in transcript.speakers
            ],
            "key_phrases": [
                {
                    "text": kp.text,
                    "rank": kp.rank,
                    "rank_percent": kp.rank_percent,
                    "count": kp.count,
                    "timestamps": kp.timestamps
                }
                for kp in transcript.key_phrases
            ],
            "chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "start_time": chunk.start_time,
                    "end_time": chunk.end_time,
                    "duration": chunk.duration,
                    "timestamp": chunk.timestamp,
                    "text": chunk.text,
                    "url_with_timestamp": chunk.url_with_timestamp,
                    "segment_ids": chunk.segment_ids,
                    "chapter_id": chunk.chapter_id,
                    "chapter_headline": chunk.chapter_headline,
                    "entities": chunk.entities,
                    "entity_types": chunk.entity_types,
                    "topics": chunk.topics,
                    "dominant_sentiment": chunk.dominant_sentiment,
                    "sentiment_confidence": chunk.sentiment_confidence,
                    "speaker": chunk.speaker
                }
                for chunk in chunks
            ]
        }

        # Save to JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"💾 AssemblyAI transcript saved to: {json_path}")

        return json_path

    def load_transcript_from_json(
        self,
        json_path: str
    ) -> Tuple[VideoTranscriptAssemblyAI, List[VideoChunkAssemblyAI]]:
        """
        Load transcript and chunks from JSON file

        Args:
            json_path: Path to JSON file

        Returns:
            Tuple (VideoTranscriptAssemblyAI, List[VideoChunkAssemblyAI])
        """
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")

        # Load JSON
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Parse segments
        segments = [
            TranscriptSegment(
                id=seg['id'],
                start=seg['start'],
                end=seg['end'],
                text=seg['text']
            )
            for seg in data['transcript']['segments']
        ]

        # Parse chapters
        chapters = [
            Chapter(
                chapter_id=ch['chapter_id'],
                start=ch['start'],
                end=ch['end'],
                headline=ch['headline'],
                summary=ch['summary'],
                gist=ch['gist']
            )
            for ch in data.get('chapters', [])
        ]

        # Parse entities
        entities = [
            Entity(
                entity_type=e['entity_type'],
                text=e['text'],
                start=e['start'],
                end=e['end']
            )
            for e in data.get('entities', [])
        ]

        # Parse topics
        topics = [
            Topic(
                topic=t['topic'],
                relevance=t['relevance']
            )
            for t in data.get('topics', [])
        ]

        # Parse sentiment segments
        sentiment_segments = [
            SentimentSegment(
                text=s['text'],
                sentiment=s['sentiment'],
                confidence=s['confidence'],
                start=s['start'],
                end=s['end'],
                speaker=s.get('speaker')
            )
            for s in data.get('sentiment_segments', [])
        ]

        # Parse speakers
        speakers = [
            Speaker(
                speaker=sp['speaker'],
                start=sp['start'],
                end=sp['end'],
                text=sp['text'],
                confidence=sp['confidence']
            )
            for sp in data.get('speakers', [])
        ]

        # Parse key phrases
        key_phrases = [
            KeyPhrase(
                text=kp['text'],
                rank=kp['rank'],
                count=kp['count'],
                timestamps=kp['timestamps']
            )
            for kp in data.get('key_phrases', [])
        ]

        # Calculate real duration from segments (fix for incorrect metadata)
        real_duration = segments[-1].end if segments else data['metadata']['duration']

        # Create VideoTranscriptAssemblyAI
        transcript = VideoTranscriptAssemblyAI(
            video_id=data['metadata']['video_id'],
            title=data['metadata']['title'],
            url=data['metadata']['url'],
            duration=real_duration,  # Use real duration from last segment
            language=data['metadata']['language'],
            segments=segments,
            chapters=chapters,
            entities=entities,
            topics=topics,
            sentiment_segments=sentiment_segments,
            speakers=speakers,
            key_phrases=key_phrases,
            audio_duration=real_duration,  # Use real duration
            confidence=data['metadata'].get('confidence', 0.0),
            words_count=data['metadata'].get('words_count', 0)
        )

        # Parse chunks (old format - will be recreated)
        # We don't use old chunks, just return empty list
        # User will call chunk_transcript() to create new chunks
        chunks = []

        print(f"📂 Transcript loaded from: {json_path}", flush=True)
        print(f"   Segments: {len(segments)}", flush=True)
        print(f"   Chapters: {len(chapters)}", flush=True)
        print(f"   Entities: {len(entities)}", flush=True)
        print(f"   Duration: {transcript.duration:.1f}s", flush=True)

        return transcript, chunks


__all__ = ['VideoProcessorAssemblyAI']
