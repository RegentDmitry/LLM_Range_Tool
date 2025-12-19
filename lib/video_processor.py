#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Video processor for transcription and chunking
Uses OpenAI Whisper API
"""

import os
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from openai import OpenAI
from models.video_models import VideoTranscript, TranscriptSegment, VideoChunk


class VideoProcessor:
    """Processor for video transcription and processing"""

    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize processor

        Args:
            openai_api_key: OpenAI API key (if not provided, reads from env variable)
        """
        api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY env variable or pass it directly.")

        self.client = OpenAI(api_key=api_key)

    def transcribe_video(
        self,
        video_path: str,
        video_id: str,
        title: str,
        url: str,
        language: str = "en"
    ) -> VideoTranscript:
        """
        Transcribe video using OpenAI Whisper API

        Args:
            video_path: Path to video file
            video_id: Unique video ID
            title: Video title
            url: Video URL
            language: Video language (default "en")

        Returns:
            VideoTranscript with segments and timestamps
        """
        print(f"📹 Transcribing video: {title}")
        print(f"   File: {video_path}")

        # Check file exists
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Transcribe via Whisper API
        with open(video_path, "rb") as audio_file:
            transcript_response = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
                language=language
            )

        # Parse segments
        segments = []
        for i, seg in enumerate(transcript_response.segments):
            segment = TranscriptSegment(
                id=i,
                start=seg.start,
                end=seg.end,
                text=seg.text.strip()
            )
            segments.append(segment)

        # Create VideoTranscript
        video_transcript = VideoTranscript(
            video_id=video_id,
            title=title,
            url=url,
            duration=transcript_response.duration,
            language=language,
            segments=segments
        )

        print(f"✓ Transcription complete: {len(segments)} segments, {video_transcript.duration:.1f}s")

        return video_transcript

    def chunk_transcript(
        self,
        transcript: VideoTranscript,
        chunk_duration: float = 60.0,
        overlap: float = 5.0
    ) -> List[VideoChunk]:
        """
        Split transcript into chunks for RAG system

        Args:
            transcript: VideoTranscript to split
            chunk_duration: Chunk duration in seconds (default 60s = 1 minute)
            overlap: Overlap between chunks in seconds (default 5s)

        Returns:
            List of VideoChunk
        """
        print(f"📦 Creating chunks for video: {transcript.title}")
        print(f"   Chunk duration: {chunk_duration}s, overlap: {overlap}s")

        chunks = []
        current_start = 0.0
        chunk_counter = 0

        while current_start < transcript.duration:
            chunk_end = min(current_start + chunk_duration, transcript.duration)

            # Find segments for this chunk
            chunk_segments = []
            chunk_text_parts = []

            for segment in transcript.segments:
                # Segment belongs to chunk if it overlaps with time window
                if segment.start < chunk_end and segment.end > current_start:
                    chunk_segments.append(segment)
                    chunk_text_parts.append(segment.text)

            if chunk_segments:
                # Create chunk
                chunk = VideoChunk(
                    chunk_id=f"{transcript.video_id}_chunk_{chunk_counter}",
                    video_id=transcript.video_id,
                    video_title=transcript.title,
                    video_url=transcript.url,
                    start_time=chunk_segments[0].start,
                    end_time=chunk_segments[-1].end,
                    text=" ".join(chunk_text_parts),
                    segment_ids=[seg.id for seg in chunk_segments]
                )
                chunks.append(chunk)
                chunk_counter += 1

            # Move to next chunk with overlap
            current_start = chunk_end - overlap

        print(f"✓ Created {len(chunks)} chunks")

        return chunks

    def process_video(
        self,
        video_path: str,
        video_id: str,
        title: str,
        url: str,
        language: str = "en",
        chunk_duration: float = 60.0,
        overlap: float = 5.0
    ) -> tuple[VideoTranscript, List[VideoChunk]]:
        """
        Full video processing: transcription + chunking

        Args:
            video_path: Path to video file
            video_id: Unique video ID
            title: Video title
            url: Video URL
            language: Video language
            chunk_duration: Chunk duration in seconds
            overlap: Overlap between chunks in seconds

        Returns:
            Tuple (VideoTranscript, List[VideoChunk])
        """
        # 1. Transcription
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
            overlap=overlap
        )

        return transcript, chunks

    def save_transcript_to_json(
        self,
        transcript: VideoTranscript,
        chunks: List[VideoChunk],
        output_dir: str = "./transcripts"
    ) -> Path:
        """
        Save transcript and chunks to JSON file

        Args:
            transcript: VideoTranscript to save
            chunks: List of VideoChunk to save
            output_dir: Output directory (default: ./transcripts)

        Returns:
            Path to saved JSON file
        """
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Create filename
        json_filename = f"{transcript.video_id}.json"
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
            "chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "start_time": chunk.start_time,
                    "end_time": chunk.end_time,
                    "duration": chunk.duration,
                    "timestamp": chunk.timestamp,
                    "text": chunk.text,
                    "url_with_timestamp": chunk.url_with_timestamp,
                    "segment_ids": chunk.segment_ids
                }
                for chunk in chunks
            ]
        }

        # Save to JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"💾 Transcript saved to: {json_path}")

        return json_path

    def load_transcript_from_json(
        self,
        json_path: str
    ) -> tuple[VideoTranscript, List[VideoChunk]]:
        """
        Load transcript and chunks from JSON file

        Args:
            json_path: Path to JSON file

        Returns:
            Tuple (VideoTranscript, List[VideoChunk])
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

        # Create VideoTranscript
        transcript = VideoTranscript(
            video_id=data['metadata']['video_id'],
            title=data['metadata']['title'],
            url=data['metadata']['url'],
            duration=data['metadata']['duration'],
            language=data['metadata']['language'],
            segments=segments
        )

        # Parse chunks
        chunks = [
            VideoChunk(
                chunk_id=chunk['chunk_id'],
                video_id=data['metadata']['video_id'],
                video_title=data['metadata']['title'],
                video_url=data['metadata']['url'],
                start_time=chunk['start_time'],
                end_time=chunk['end_time'],
                text=chunk['text'],
                segment_ids=chunk['segment_ids']
            )
            for chunk in data['chunks']
        ]

        print(f"📂 Transcript loaded from: {json_path}")
        print(f"   Segments: {len(segments)}")
        print(f"   Chunks: {len(chunks)}")

        return transcript, chunks


__all__ = ['VideoProcessor']
