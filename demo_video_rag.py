#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for Video RAG system demo
Shows full cycle: transcription → indexing → search
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from lib.video_processor import VideoProcessor
from lib.video_rag import VideoRAG

# Load .env file
load_dotenv()


def format_size(size_bytes):
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def check_video_file(file_path):
    """
    Check if video file is valid for Whisper API

    Returns:
        tuple: (is_valid, error_message)
    """
    path = Path(file_path)

    # Check if file exists
    if not path.exists():
        return False, f"File not found: {file_path}"

    # Get file size
    size_bytes = path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)

    print(f"📁 File info:")
    print(f"   Name: {path.name}")
    print(f"   Size: {format_size(size_bytes)} ({size_mb:.2f} MB)")
    print(f"   Extension: {path.suffix}")
    print()

    # Check file size (Whisper API limit: 25MB)
    if size_mb > 25:
        return False, f"File too large: {size_mb:.2f} MB (max 25 MB for Whisper API)"

    # Check supported formats
    supported_formats = ['.mp4', '.mp3', '.wav', '.m4a', '.webm', '.mpeg', '.mpga']
    if path.suffix.lower() not in supported_formats:
        return False, f"Unsupported format: {path.suffix}. Supported: {', '.join(supported_formats)}"

    return True, None


def main():
    """Main demonstration function"""

    print("=" * 70)
    print("🎬 Video RAG System - Demo")
    print("=" * 70)
    print()

    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in .env file")
        print("   Add your OpenAI API key to .env:")
        print("   OPENAI_API_KEY=sk-your-key-here")
        return

    print(f"✓ OpenAI API key found: {api_key[:20]}...")
    print()

    # ==================================================================
    # STEP 1: Transcribe test video
    # ==================================================================
    print("=" * 70)
    print("📝 STEP 1: Video Transcription")
    print("=" * 70)
    print()

    # For demo purposes, use a short test video
    # REPLACE with path to your video
    test_video_path = input("Enter path to video file (or Enter to skip): ").strip()

    if not test_video_path:
        print("⚠️  Video file not specified")
        print()
        print("💡 Usage example:")
        print("   1. Download a short poker tutorial video (under 25MB)")
        print("   2. Run the script again and provide the file path")
        print()
        print("📚 What this script does:")
        print("   ✓ Transcribes video via OpenAI Whisper API")
        print("   ✓ Creates chunks with timestamps (60 seconds each)")
        print("   ✓ Saves transcript to JSON (./transcripts/)")
        print("   ✓ Vectorizes text via OpenAI Embeddings")
        print("   ✓ Saves to ChromaDB (local vector DB)")
        print("   ✓ Allows searching video content")
        print()
        print("⚠️  Important: Whisper API has 25MB file size limit!")
        print("   If your file is larger, compress it first or cut to shorter length")
        print()
        return

    # Check video file
    is_valid, error_msg = check_video_file(test_video_path)
    if not is_valid:
        print(f"❌ {error_msg}")
        print()
        print("💡 Solutions:")
        print("   1. Use a smaller file (under 25MB)")
        print("   2. Compress the video (use Handbrake, FFmpeg, etc.)")
        print("   3. Cut to a shorter segment for testing")
        print()
        return

    # Initialize processor
    print("🔧 Initializing processor...")
    processor = VideoProcessor(openai_api_key=api_key)
    print()

    # Transcribe
    print("🎤 Starting transcription...")
    print("   This may take a few minutes depending on video length...")
    print("   (Progress is shown by OpenAI)")
    print()

    try:
        transcript, chunks = processor.process_video(
            video_path=test_video_path,
            video_id="test_video_001",
            title="Test poker tutorial video",
            url="https://example.com/video/001",
            language="en",  # Change to "ru" for Russian videos
            chunk_duration=60.0,  # 1 minute per chunk
            overlap=5.0  # 5 seconds overlap
        )

        print()
        print("=" * 70)
        print(f"✅ Transcription completed successfully!")
        print("=" * 70)
        print()
        print(f"📊 Transcription stats:")
        print(f"   Duration: {transcript.duration:.1f} seconds ({transcript.duration/60:.1f} minutes)")
        print(f"   Segments: {transcript.segment_count}")
        print(f"   Chunks created: {len(chunks)}")
        print()

        # Show first 3 chunks
        print("📝 Sample chunks:")
        for i, chunk in enumerate(chunks[:3], 1):
            print(f"\n   [{i}] Chunk {chunk.chunk_id}")
            print(f"       Timestamp: {chunk.timestamp}")
            print(f"       Text: {chunk.text[:150]}...")

        # Save transcript to JSON
        print()
        print("💾 Saving transcript to JSON...")
        try:
            json_path = processor.save_transcript_to_json(transcript, chunks)
            print(f"✓ Saved to: {json_path}")
        except Exception as e:
            print(f"⚠️  Warning: Could not save JSON: {e}")
            print("   (Continuing with vector DB indexing...)")

    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ Transcription error")
        print("=" * 70)
        print(f"Error: {str(e)}")
        print()

        # Provide helpful error messages
        error_str = str(e).lower()
        if "400" in error_str or "invalid" in error_str:
            print("💡 Possible solutions:")
            print("   1. File might be corrupted - try a different file")
            print("   2. File format might not be supported")
            print("   3. Try converting to MP3 or MP4 format")
            print("   4. Make sure file is under 25MB")
        elif "401" in error_str or "authentication" in error_str:
            print("💡 API key issue:")
            print("   Check your OPENAI_API_KEY in .env file")
        elif "429" in error_str or "rate" in error_str:
            print("💡 Rate limit reached:")
            print("   Wait a few minutes and try again")
        elif "insufficient" in error_str or "quota" in error_str:
            print("💡 Insufficient credits:")
            print("   Add credits to your OpenAI account")
            print("   Visit: https://platform.openai.com/settings/organization/billing/overview")

        print()
        return

    print()

    # ==================================================================
    # STEP 2: Index into vector DB
    # ==================================================================
    print("=" * 70)
    print("🗄️  STEP 2: Index into vector DB")
    print("=" * 70)
    print()

    # Initialize RAG system
    print("🔧 Initializing ChromaDB...")
    rag = VideoRAG(
        openai_api_key=api_key,
        collection_name="poker_videos",
        persist_directory="./chroma_db"
    )
    print()

    # Add chunks to DB
    print(f"📥 Adding {len(chunks)} chunks to vector database...")
    print("   This will create embeddings via OpenAI API...")
    print()

    try:
        rag.add_chunks(chunks)
    except Exception as e:
        print(f"❌ Error adding chunks: {e}")
        return

    # DB statistics
    stats = rag.get_stats()
    print()
    print("=" * 70)
    print("✅ Indexing completed!")
    print("=" * 70)
    print()
    print(f"📊 DB Statistics:")
    print(f"   Total chunks: {stats['total_chunks']}")
    print(f"   Unique videos: {stats['unique_videos']}")
    print()

    # ==================================================================
    # STEP 3: Search videos
    # ==================================================================
    print("=" * 70)
    print("🔍 STEP 3: Search video content")
    print("=" * 70)
    print()

    # Sample search queries
    test_queries = [
        "preflop strategy",
        "bluffing on the river",
        "bet sizing",
    ]

    print("💬 Test queries:")
    for i, query in enumerate(test_queries, 1):
        print(f"   [{i}] {query}")

    print()
    print("Select query number (1-3) or enter your own:")
    user_input = input("> ").strip()

    if user_input.isdigit() and 1 <= int(user_input) <= 3:
        query = test_queries[int(user_input) - 1]
    else:
        query = user_input if user_input else test_queries[0]

    print()
    print(f"🔍 Searching: '{query}'")
    print()

    # Search
    try:
        results = rag.search(query=query, top_k=3)
    except Exception as e:
        print(f"❌ Search error: {e}")
        return

    if not results:
        print("❌ No results found")
        print("   Try a different search query")
    else:
        print(f"✓ Found {len(results)} results:")
        print()

        for i, result in enumerate(results, 1):
            print(f"{'=' * 70}")
            print(f"Result {i}:")
            print(result.formatted_result)

    # ==================================================================
    # INTERACTIVE MODE
    # ==================================================================
    print()
    print("=" * 70)
    print("💬 Interactive Search")
    print("=" * 70)
    print()
    print("Enter search query (or 'quit' to exit):")
    print()

    while True:
        try:
            user_query = input("Your query > ").strip()

            if user_query.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break

            if not user_query:
                continue

            print()
            results = rag.search(query=user_query, top_k=3)

            if not results:
                print("❌ No results found\n")
            else:
                for i, result in enumerate(results, 1):
                    print(f"\n{'─' * 70}")
                    print(f"[{i}] {result.chunk.video_title}")
                    print(f"⏱️  {result.chunk.timestamp} | 📊 {result.score:.1%}")
                    print(f"🔗 {result.chunk.url_with_timestamp}")
                    print(f"💬 {result.chunk.text[:200]}...")
                    print()

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    main()
