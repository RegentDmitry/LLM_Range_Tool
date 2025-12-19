#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Demo script for Video RAG system with AssemblyAI
Shows advanced features: chapters, entities, topics, sentiment, speaker diarization
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from lib.video_processor_assemblyai import VideoProcessorAssemblyAI
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
    Check if video file is valid

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

    # AssemblyAI supports larger files than Whisper
    if size_mb > 500:
        return False, f"File too large: {size_mb:.2f} MB (recommended max 500 MB)"

    # Check supported formats
    supported_formats = ['.mp4', '.mp3', '.wav', '.m4a', '.webm', '.mpeg', '.mpga', '.flac', '.ogg']
    if path.suffix.lower() not in supported_formats:
        return False, f"Unsupported format: {path.suffix}. Supported: {', '.join(supported_formats)}"

    return True, None


def display_advanced_features(transcript):
    """Display all advanced features from AssemblyAI"""

    # Chapters
    if transcript.chapters:
        print("\n" + "=" * 70)
        print(f"📖 AUTO CHAPTERS ({len(transcript.chapters)} chapters)")
        print("=" * 70)
        for i, chapter in enumerate(transcript.chapters[:5], 1):  # Show first 5
            print(f"\n[{i}] {chapter.headline}")
            print(f"    ⏱️  {chapter.timestamp} - {chapter.duration:.0f}s")
            print(f"    📝 {chapter.summary[:150]}...")
        if len(transcript.chapters) > 5:
            print(f"\n... and {len(transcript.chapters) - 5} more chapters")

    # Topics
    if transcript.topics:
        print("\n" + "=" * 70)
        print(f"🏷️  TOPICS DETECTED ({len(transcript.topics)} topics)")
        print("=" * 70)
        top_topics = sorted(transcript.topics, key=lambda t: t.relevance, reverse=True)[:10]
        for topic in top_topics:
            print(f"   • {topic.topic}: {topic.relevance_percent}")

    # Entities
    if transcript.entities:
        print("\n" + "=" * 70)
        print(f"🎯 ENTITIES DETECTED ({len(transcript.entities)} entities)")
        print("=" * 70)
        # Group by type
        entities_by_type = {}
        for entity in transcript.entities:
            if entity.entity_type not in entities_by_type:
                entities_by_type[entity.entity_type] = []
            entities_by_type[entity.entity_type].append(entity.text)

        for entity_type, texts in entities_by_type.items():
            unique_texts = list(set(texts))[:5]  # Show up to 5 unique
            print(f"   {entity_type}: {', '.join(unique_texts)}")
            if len(unique_texts) > 5:
                print(f"      (+{len(set(texts)) - 5} more)")

    # Speakers
    if transcript.speakers:
        print("\n" + "=" * 70)
        print(f"🎤 SPEAKERS ({transcript.speaker_count} speakers)")
        print("=" * 70)
        # Show first utterance from each speaker
        seen_speakers = set()
        for speaker in transcript.speakers:
            if speaker.speaker not in seen_speakers:
                seen_speakers.add(speaker.speaker)
                print(f"\n   Speaker {speaker.speaker}:")
                print(f"      {speaker.text[:150]}...")
                print(f"      (Confidence: {speaker.confidence:.1%})")

    # Sentiment
    if transcript.sentiment_segments:
        print("\n" + "=" * 70)
        print(f"😊 SENTIMENT ANALYSIS")
        print("=" * 70)
        summary = transcript.sentiment_summary
        total = sum(summary.values())
        if total > 0:
            print(f"   😊 Positive: {summary['POSITIVE']} ({summary['POSITIVE']/total:.1%})")
            print(f"   😐 Neutral:  {summary['NEUTRAL']} ({summary['NEUTRAL']/total:.1%})")
            print(f"   😞 Negative: {summary['NEGATIVE']} ({summary['NEGATIVE']/total:.1%})")

        # Show some examples
        print("\n   Sample sentiments:")
        for sent in transcript.sentiment_segments[:3]:
            print(f"      {sent.sentiment_emoji} {sent.sentiment} ({sent.confidence:.0%}): {sent.text[:100]}...")

    # Key phrases
    if transcript.key_phrases:
        print("\n" + "=" * 70)
        print(f"🔑 KEY PHRASES ({len(transcript.key_phrases)} phrases)")
        print("=" * 70)
        top_phrases = sorted(transcript.key_phrases, key=lambda p: p.rank, reverse=True)[:10]
        for phrase in top_phrases:
            print(f"   • {phrase.text} (importance: {phrase.rank_percent}, count: {phrase.count})")


def main():
    """Main demonstration function"""

    print("=" * 70)
    print("🎬 Video RAG System - AssemblyAI Edition")
    print("=" * 70)
    print()
    print("✨ Advanced Features:")
    print("   ✓ Auto Chapters with summaries")
    print("   ✓ Entity Detection (people, places, organizations)")
    print("   ✓ Topic Detection (automatic categorization)")
    print("   ✓ Sentiment Analysis (positive/negative/neutral)")
    print("   ✓ Speaker Diarization (who said what)")
    print("   ✓ Key Phrases (important highlights)")
    print()

    # Check API keys
    openai_key = os.getenv('OPENAI_API_KEY')
    assemblyai_key = os.getenv('ASSEMBLYAI_API_KEY')

    if not assemblyai_key:
        print("❌ ASSEMBLYAI_API_KEY not found in .env file")
        print("   Add your AssemblyAI API key to .env:")
        print("   ASSEMBLYAI_API_KEY=your-key-here")
        print()
        print("💡 Get your API key at: https://www.assemblyai.com/")
        return

    if not openai_key:
        print("⚠️  OPENAI_API_KEY not found (needed for embeddings)")
        print("   Add your OpenAI API key to .env:")
        print("   OPENAI_API_KEY=sk-your-key-here")
        print()

    print(f"✓ AssemblyAI API key found: {assemblyai_key[:20]}...")
    if openai_key:
        print(f"✓ OpenAI API key found: {openai_key[:20]}...")
    print()

    # ==================================================================
    # STEP 1: Transcribe video with AssemblyAI
    # ==================================================================
    print("=" * 70)
    print("📝 STEP 1: Video Transcription with AssemblyAI")
    print("=" * 70)
    print()

    test_video_path = input("Enter path to video file (or Enter to skip): ").strip()

    if not test_video_path:
        print("⚠️  Video file not specified")
        print()
        print("💡 Usage example:")
        print("   1. Download a poker tutorial video (AssemblyAI supports up to 500MB)")
        print("   2. Run the script again and provide the file path")
        print()
        print("📚 What this script does:")
        print("   ✓ Transcribes video via AssemblyAI API")
        print("   ✓ Generates auto chapters with summaries")
        print("   ✓ Detects entities, topics, sentiment")
        print("   ✓ Identifies speakers (if multiple people)")
        print("   ✓ Saves enhanced transcript to JSON")
        print("   ✓ Indexes to ChromaDB for semantic search")
        print()
        return

    # Check video file
    is_valid, error_msg = check_video_file(test_video_path)
    if not is_valid:
        print(f"❌ {error_msg}")
        return

    # Initialize processor
    print("🔧 Initializing AssemblyAI processor...")
    processor = VideoProcessorAssemblyAI(assemblyai_api_key=assemblyai_key)
    print()

    # Transcribe
    print("🎤 Starting transcription with AssemblyAI...")
    print("   This will take a few minutes...")
    print()

    try:
        transcript, chunks = processor.process_video(
            video_path=test_video_path,
            video_id="test_video_assemblyai_001",
            title="Test poker tutorial video (AssemblyAI)",
            url="https://example.com/video/001",
            language="en",  # Change to "ru" for Russian
            use_chapters=True  # Use chapter-based chunking
        )

        print()
        print("=" * 70)
        print(f"✅ Transcription completed successfully!")
        print("=" * 70)
        print()

        # Display advanced features
        display_advanced_features(transcript)

        # Save to JSON
        print()
        print("=" * 70)
        print("💾 Saving enhanced transcript to JSON...")
        print("=" * 70)
        try:
            json_path = processor.save_transcript_to_json(transcript, chunks)
            print(f"✓ Saved to: {json_path}")
        except Exception as e:
            print(f"⚠️  Warning: Could not save JSON: {e}")

    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ Transcription error")
        print("=" * 70)
        print(f"Error: {str(e)}")
        print()

        error_str = str(e).lower()
        if "401" in error_str or "authentication" in error_str:
            print("💡 API key issue:")
            print("   Check your ASSEMBLYAI_API_KEY in .env file")
        elif "429" in error_str or "rate" in error_str:
            print("💡 Rate limit reached:")
            print("   Wait a few minutes and try again")
        elif "insufficient" in error_str or "quota" in error_str:
            print("💡 Insufficient credits:")
            print("   Add credits to your AssemblyAI account")

        print()
        return

    # ==================================================================
    # STEP 2: Index into vector DB (if OpenAI key available)
    # ==================================================================
    if not openai_key:
        print()
        print("⚠️  Skipping ChromaDB indexing (OpenAI API key needed for embeddings)")
        print("   Add OPENAI_API_KEY to .env to enable semantic search")
        return

    print()
    print("=" * 70)
    print("🗄️  STEP 2: Index into ChromaDB")
    print("=" * 70)
    print()

    # Initialize RAG system
    print("🔧 Initializing ChromaDB...")
    rag = VideoRAG(
        openai_api_key=openai_key,
        collection_name="poker_videos_assemblyai",
        persist_directory="./chroma_db_assemblyai"
    )
    print()

    # Add chunks to DB
    print(f"📥 Adding {len(chunks)} enhanced chunks to vector database...")
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
    # STEP 3: Interactive search
    # ==================================================================
    print("=" * 70)
    print("🔍 STEP 3: Semantic Search")
    print("=" * 70)
    print()
    print("💡 Try searching for:")
    print("   • Specific topics (e.g., 'preflop strategy')")
    print("   • Concepts (e.g., 'pot odds')")
    print("   • Players or names")
    print("   • Emotional content (will show sentiment)")
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
                    chunk = result.chunk
                    print(f"\n{'─' * 70}")
                    print(f"[{i}] {chunk.video_title}")
                    print(f"⏱️  {chunk.timestamp} | 📊 Relevance: {result.score:.1%}")

                    # Show chapter info if available
                    if hasattr(chunk, 'chapter_headline') and chunk.chapter_headline:
                        print(f"📖 Chapter: {chunk.chapter_headline}")

                    # Show entities if available
                    if hasattr(chunk, 'entities') and chunk.entities:
                        print(f"🎯 Entities: {', '.join(chunk.entities[:3])}")

                    # Show sentiment if available
                    if hasattr(chunk, 'dominant_sentiment') and chunk.dominant_sentiment:
                        emoji = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}.get(chunk.dominant_sentiment, "")
                        print(f"{emoji} Sentiment: {chunk.dominant_sentiment}")

                    print(f"🔗 {chunk.url_with_timestamp}")
                    print(f"💬 {chunk.text[:200]}...")
                    print()

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    main()
