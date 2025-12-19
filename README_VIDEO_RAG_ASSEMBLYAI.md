# Video RAG System - AssemblyAI Edition

AI-powered video content search with **advanced features**: auto chapters, entity detection, topic classification, sentiment analysis, and speaker diarization.

## Why AssemblyAI?

While OpenAI Whisper provides excellent basic transcription, **AssemblyAI unlocks deep video understanding**:

| Feature | OpenAI Whisper | AssemblyAI |
|---------|----------------|------------|
| Basic transcription | ✅ | ✅ |
| Timestamps | ✅ | ✅ |
| **Auto Chapters** | ❌ | ✅ |
| **Speaker Diarization** | ❌ | ✅ |
| **Entity Detection** | ❌ | ✅ |
| **Topic Classification** | ❌ | ✅ |
| **Sentiment Analysis** | ❌ | ✅ |
| **Key Phrases** | ❌ | ✅ |
| File size limit | 25MB | 500MB |
| Cost per minute | $0.006 | $0.025 |

**4x more expensive, but 10x more powerful for serious applications.**

## Features

### 📖 Auto Chapters
- Automatically splits video into logical sections
- Generates headlines and summaries for each chapter
- Perfect for long educational content

### 🎯 Entity Detection
- Identifies people, places, organizations
- Extracts poker terms, player names, positions
- Great for finding specific references

### 🏷️ Topic Classification
- Categorizes content using IAB taxonomy
- Detects main themes (strategy, math, psychology)
- Helps organize large video libraries

### 😊 Sentiment Analysis
- Tracks emotional tone (positive/negative/neutral)
- Per-segment sentiment with confidence scores
- Useful for finding exciting/critical moments

### 🎤 Speaker Diarization
- Identifies who said what
- Separates multiple speakers
- Perfect for interviews, discussions, coaching sessions

### 🔑 Key Phrases
- Extracts most important phrases
- Ranks by importance and frequency
- Quick overview of main concepts

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Add your API key to .env
echo "ASSEMBLYAI_API_KEY=your-key-here" >> .env
echo "OPENAI_API_KEY=your-openai-key" >> .env  # For embeddings
```

Get your AssemblyAI API key: https://www.assemblyai.com/

## Quick Start

```bash
python demo_video_rag_assemblyai.py
```

Enter video path when prompted, and watch the magic happen!

## Cost

**AssemblyAI Pricing:**
- Transcription: **$0.025/minute** ($1.50/hour of video)
- All advanced features included (no extra cost)
- OpenAI Embeddings: **$0.02/1M tokens** (~$0.10/hour)

**Total: ~$1.60/hour of video**

Worth it for:
- Educational content with chapters
- Multi-speaker videos (podcasts, interviews)
- Content that needs categorization
- Analysis of sentiment/tone
- Professional video libraries

## Usage Example

### Basic Usage

```python
from lib.video_processor_assemblyai import VideoProcessorAssemblyAI
from lib.video_rag import VideoRAG

# 1. Transcribe with all features
processor = VideoProcessorAssemblyAI()
transcript, chunks = processor.process_video(
    video_path="tutorial.mp4",
    video_id="video_001",
    title="Advanced PLO5 Strategy",
    url="https://youtube.com/watch?v=abc123",
    language="en",
    use_chapters=True  # Chunk by chapters instead of time
)

# 2. Access advanced features
print(f"Chapters: {len(transcript.chapters)}")
print(f"Entities: {len(transcript.entities)}")
print(f"Topics: {transcript.top_topics}")
print(f"Speakers: {transcript.speaker_count}")

# 3. Index to vector DB
rag = VideoRAG(collection_name="poker_videos")
rag.add_chunks(chunks)

# 4. Search with enhanced metadata
results = rag.search("preflop strategy", top_k=5)
for result in results:
    print(f"Chapter: {result.chunk.chapter_headline}")
    print(f"Entities: {result.chunk.entities}")
    print(f"Sentiment: {result.chunk.dominant_sentiment}")
```

### Advanced Features Example

```python
# Explore chapters
for chapter in transcript.chapters:
    print(f"{chapter.timestamp} - {chapter.headline}")
    print(f"Summary: {chapter.summary}")
    print(f"Gist: {chapter.gist}")
    print()

# Find entities
entities_by_type = {}
for entity in transcript.entities:
    if entity.entity_type not in entities_by_type:
        entities_by_type[entity.entity_type] = []
    entities_by_type[entity.entity_type].append(entity.text)

print("People mentioned:", entities_by_type.get('person', []))
print("Locations:", entities_by_type.get('location', []))

# Analyze sentiment
sentiment_summary = transcript.sentiment_summary
total = sum(sentiment_summary.values())
print(f"Positive: {sentiment_summary['POSITIVE']/total:.1%}")
print(f"Neutral: {sentiment_summary['NEUTRAL']/total:.1%}")
print(f"Negative: {sentiment_summary['NEGATIVE']/total:.1%}")

# Speaker analysis
for speaker in transcript.speakers:
    print(f"Speaker {speaker.speaker}: {speaker.text[:100]}...")

# Key phrases
for phrase in transcript.key_phrases[:10]:
    print(f"• {phrase.text} (importance: {phrase.rank:.1%})")
```

## Project Structure

```
├── models/
│   ├── video_models.py                    # Base models
│   └── video_models_assemblyai.py         # Extended models with advanced features
├── lib/
│   ├── video_processor.py                 # OpenAI Whisper version
│   ├── video_processor_assemblyai.py      # AssemblyAI version (this one!)
│   └── video_rag.py                       # RAG search system
├── demo_video_rag_assemblyai.py           # Interactive demo
├── transcripts_assemblyai/                # JSON storage (created automatically)
├── chroma_db_assemblyai/                  # ChromaDB storage (created automatically)
└── README_VIDEO_RAG_ASSEMBLYAI.md         # This file
```

## Enhanced Data Models

### VideoTranscriptAssemblyAI

Extends `VideoTranscript` with:
- `chapters: List[Chapter]` - Auto-generated chapters
- `entities: List[Entity]` - Named entities
- `topics: List[Topic]` - Topic classifications
- `sentiment_segments: List[SentimentSegment]` - Sentiment analysis
- `speakers: List[Speaker]` - Speaker diarization
- `key_phrases: List[KeyPhrase]` - Important phrases

### VideoChunkAssemblyAI

Extends `VideoChunk` with:
- `chapter_id: int` - Chapter this chunk belongs to
- `chapter_headline: str` - Chapter title
- `entities: List[str]` - Entities in chunk
- `topics: List[str]` - Topics for this chunk
- `dominant_sentiment: str` - Overall sentiment
- `speaker: str` - Speaker label if applicable

## Use Cases

### 1. Educational Video Library

```python
# Process entire library
for video_file in glob.glob("videos/*.mp4"):
    transcript, chunks = processor.process_video(...)

    # Chunks automatically organized by chapters
    for chunk in chunks:
        print(f"Chapter: {chunk.chapter_headline}")
        print(f"Topics: {chunk.topics}")
```

### 2. Podcast/Interview Indexing

```python
# Speaker diarization automatically enabled
transcript, chunks = processor.process_video(
    video_path="podcast_episode_42.mp4",
    ...
)

# Access speaker information
for speaker in transcript.speakers:
    print(f"Speaker {speaker.speaker}:")
    print(f"  {speaker.text}")
```

### 3. Content Analysis

```python
# Analyze sentiment across video
positive_chunks = [
    c for c in chunks
    if c.dominant_sentiment == "POSITIVE"
]
negative_chunks = [
    c for c in chunks
    if c.dominant_sentiment == "NEGATIVE"
]

print(f"Positive moments: {len(positive_chunks)}")
print(f"Negative/critical moments: {len(negative_chunks)}")
```

### 4. Entity Extraction

```python
# Find all mentions of specific players
phil_mentions = [
    e for e in transcript.entities
    if "phil" in e.text.lower() and e.entity_type == "person"
]

for mention in phil_mentions:
    print(f"At {mention.timestamp}: {mention.text}")
```

## Configuration Options

### Disable Specific Features

```python
transcript = processor.transcribe_video(
    video_path="video.mp4",
    ...,
    enable_chapters=True,      # Auto chapters
    enable_entities=True,      # Entity detection
    enable_topics=True,        # Topic detection
    enable_sentiment=True,     # Sentiment analysis
    enable_speakers=True,      # Speaker diarization
    enable_highlights=True     # Key phrases
)
```

Disable features you don't need to reduce processing time (though cost is the same).

### Chunking Strategy

```python
# Option 1: Chapter-based chunking (recommended)
chunks = processor.chunk_transcript(
    transcript,
    use_chapters=True  # Split at chapter boundaries
)

# Option 2: Time-based chunking
chunks = processor.chunk_transcript(
    transcript,
    use_chapters=False,
    chunk_duration=120.0,  # 2 minutes
    overlap=10.0           # 10 seconds overlap
)
```

## JSON Output Format

The enhanced JSON includes all advanced features:

```json
{
  "metadata": {
    "video_id": "video_001",
    "title": "Advanced PLO5 Strategy",
    "chapter_count": 8,
    "entity_count": 45,
    "speaker_count": 2,
    "top_topics": ["Sports>Poker", "Education", "Strategy"],
    "sentiment_summary": {
      "POSITIVE": 120,
      "NEUTRAL": 85,
      "NEGATIVE": 15
    }
  },
  "chapters": [...],
  "entities": [...],
  "topics": [...],
  "sentiment_segments": [...],
  "speakers": [...],
  "key_phrases": [...],
  "chunks": [...]
}
```

## Performance

- **Transcription speed**: ~1x real-time (1 hour video = ~1 hour processing)
- **File size**: Supports up to 500MB (vs 25MB for Whisper)
- **Accuracy**: Industry-leading for English content
- **Languages**: 50+ languages supported

## Comparison with Whisper

| Aspect | Use Whisper | Use AssemblyAI |
|--------|-------------|----------------|
| Budget tight | ✅ ($0.006/min) | ❌ ($0.025/min) |
| Basic transcription only | ✅ | ⚠️ (overkill) |
| Need chapters | ❌ | ✅ |
| Multiple speakers | ❌ | ✅ |
| Content categorization | ❌ | ✅ |
| Sentiment analysis | ❌ | ✅ |
| Large files (>25MB) | ❌ | ✅ |
| Professional use | ⚠️ | ✅ |

## Troubleshooting

### "API key not found"

```bash
# Add to .env file
ASSEMBLYAI_API_KEY=your-key-here
```

### "File too large"

AssemblyAI supports up to 500MB. If larger:
```bash
# Compress with ffmpeg
ffmpeg -i input.mp4 -vcodec h264 -acodec aac output.mp4
```

### Missing features in output

Check that features are enabled in `transcribe_video()`:
```python
enable_chapters=True,
enable_entities=True,
# etc.
```

## Next Steps

1. ✅ Test with a video
2. 📊 Explore advanced features
3. 🔍 Build search interface
4. 🚀 Deploy as web service

## Support

For issues:
- AssemblyAI docs: https://www.assemblyai.com/docs
- API status: https://status.assemblyai.com/

## License

Private project
