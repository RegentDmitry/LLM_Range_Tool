# Video RAG System

AI-powered video content search using OpenAI Whisper API and ChromaDB.

## Overview

This system allows you to:
1. **Transcribe** videos using OpenAI Whisper API
2. **Index** transcripts with timestamps into ChromaDB
3. **Search** video content using natural language queries
4. **Get results** with direct links to specific timestamps

Perfect for indexing thousands of educational videos and making content searchable.

## Features

- ✅ Automatic video transcription via Whisper API
- ✅ Intelligent chunking with timestamps
- ✅ Vector search using OpenAI embeddings
- ✅ Local storage with ChromaDB (no external DB needed)
- ✅ YouTube timestamp links support
- ✅ Multi-language support

## Cost

Using only your **OpenAI API key**:
- Transcription: **$0.006/minute** ($0.36/hour of video)
- Embeddings: **$0.02/1M tokens** (very cheap)
- Total: ~$0.40/hour of video

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup OpenAI API Key

Make sure your `.env` file contains:

```
OPENAI_API_KEY=sk-your-key-here
```

### 3. Run Demo Script

```bash
python demo_video_rag.py
```

This will:
1. Ask for a video file path
2. Transcribe the video
3. Create searchable chunks
4. Allow interactive search

## Project Structure

```
├── models/
│   └── video_models.py          # Pydantic models for video data
├── lib/
│   ├── video_processor.py       # Transcription + chunking
│   └── video_rag.py            # RAG search system
├── demo_video_rag.py            # Interactive demo script
├── chroma_db/                   # ChromaDB storage (created automatically)
└── README_VIDEO_RAG.md          # This file
```

## Usage Example

```python
from lib.video_processor import VideoProcessor
from lib.video_rag import VideoRAG

# 1. Transcribe video
processor = VideoProcessor()
transcript, chunks = processor.process_video(
    video_path="tutorial.mp4",
    video_id="video_001",
    title="Poker Tutorial",
    url="https://youtube.com/watch?v=abc123",
    language="en"
)

# 2. Index into vector DB
rag = VideoRAG()
rag.add_chunks(chunks)

# 3. Search
results = rag.search("preflop strategy", top_k=5)

# 4. Display results
for result in results:
    print(f"Found at {result.chunk.timestamp}")
    print(f"Link: {result.chunk.url_with_timestamp}")
    print(f"Text: {result.chunk.text}")
```

## How It Works

### 1. Transcription

```
Video File → OpenAI Whisper API → Transcript with Timestamps
```

- Processes video/audio files
- Returns segments with start/end times
- Supports multiple languages

### 2. Chunking

```
Transcript → 60-second Chunks (with 5s overlap) → VideoChunk objects
```

- Splits long transcripts into manageable pieces
- Maintains temporal context with overlaps
- Each chunk has URL with timestamp

### 3. Indexing

```
Chunks → OpenAI Embeddings → ChromaDB Vector Storage
```

- Converts text to vectors using OpenAI
- Stores in local ChromaDB database
- Persistent storage (survives restarts)

### 4. Search

```
User Query → Embedding → Vector Search → Ranked Results with Timestamps
```

- Natural language queries
- Semantic search (understands meaning, not just keywords)
- Returns most relevant chunks with timestamps

## Configuration

### Chunk Duration

Default: 60 seconds per chunk

```python
processor.process_video(
    ...,
    chunk_duration=120.0,  # 2 minutes per chunk
    overlap=10.0          # 10 seconds overlap
)
```

### Search Parameters

```python
results = rag.search(
    query="bluffing strategy",
    top_k=10,              # Get 10 results
    video_id="video_001"   # Search only specific video (optional)
)
```

### Language Support

```python
transcript = processor.transcribe_video(
    ...,
    language="ru"  # Russian
    # language="en"  # English (default)
    # language="es"  # Spanish
    # etc.
)
```

## Pydantic Models

### VideoTranscript

```python
class VideoTranscript(BaseModel):
    video_id: str
    title: str
    url: str
    duration: float
    language: str
    segments: List[TranscriptSegment]
```

### VideoChunk

```python
class VideoChunk(BaseModel):
    chunk_id: str
    video_id: str
    video_title: str
    video_url: str
    start_time: float
    end_time: float
    text: str
    segment_ids: List[int]
```

### SearchResult

```python
class SearchResult(BaseModel):
    chunk: VideoChunk
    score: float  # Relevance 0-1
```

## Advanced Features

### Clear Database

```python
rag = VideoRAG()
rag.clear_collection()  # Delete all indexed videos
```

### Get Statistics

```python
stats = rag.get_stats()
print(f"Total chunks: {stats['total_chunks']}")
print(f"Unique videos: {stats['unique_videos']}")
```

### Custom Collection

```python
rag = VideoRAG(
    collection_name="my_poker_videos",
    persist_directory="./my_custom_db"
)
```

## Scaling to Thousands of Videos

For processing many videos:

1. **Batch Processing Script** (create your own):
```python
import glob
from lib.video_processor import VideoProcessor
from lib.video_rag import VideoRAG

processor = VideoProcessor()
rag = VideoRAG()

for video_file in glob.glob("videos/*.mp4"):
    transcript, chunks = processor.process_video(
        video_path=video_file,
        video_id=Path(video_file).stem,
        title=Path(video_file).stem,
        url=f"https://yoursite.com/videos/{Path(video_file).stem}"
    )
    rag.add_chunks(chunks)
```

2. **Cost Estimation**:
- 1,000 hours of video = ~$400 for transcription
- Embeddings = ~$10-20
- Total = ~$420

3. **Storage**:
- ChromaDB stores locally
- ~100MB per 100 hours of video
- Can scale to millions of chunks

## Troubleshooting

### "OpenAI API key not found"

Make sure `.env` file exists with:
```
OPENAI_API_KEY=sk-your-actual-key
```

### "Video file not found"

Use absolute path or verify file exists:
```python
from pathlib import Path
assert Path("video.mp4").exists()
```

### ChromaDB errors

Delete and recreate:
```bash
rm -rf chroma_db/
```

Then run script again.

## Next Steps

1. ✅ Test with a short video
2. 📊 Process your video library
3. 🔍 Build search interface
4. 🚀 Deploy as web service (see PROJECT_ARCHITECTURE.md)

## Support

For issues or questions:
- Check existing issues on GitHub
- Create new issue with error details
- Include Python version and OS info

## License

Private project
