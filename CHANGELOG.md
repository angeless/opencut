# Changelog

## [1.0.0] - 2026-02-19

### 🎉 Initial Release

OpenCut - AI-powered travel video editing system for 8TB+ material libraries.

### ✨ Features

#### Asset Management
- **Video Fingerprinting**: Perceptual Hash (pHash) for duplicate detection
- **Semantic Search**: CLIP-based visual content understanding
- **Deduplication**: Automatic grouping of similar videos

#### Script Engine
- **Adaptive Rewriting**: Auto-adjust scripts when materials are missing
- **3-Level Confirmation**: Script → Material correction → Preview approval
- **Emotion Curve**: AI-driven narrative flow optimization

#### Render Pipeline
- **Beauty Filter**: Smart skin smoothing with facial feature preservation
- **Color Grading**: Cinematic LUTs with skin tone protection (YUV)
- **Bilingual Subtitles**: Auto-generated Chinese/English captions
- **Beat Sync**: BPM-aligned video cuts

### 🧪 Test Results

All 4 end-to-end tests passing:
- ✅ Fingerprint indexing (2 videos, 16 frames sampled)
- ✅ Semantic search (CLIP framework ready)
- ✅ Adaptive script (auto-rewrite on material gaps)
- ✅ Render pipeline (full workflow executed)

### 🛠️ Installation

```bash
git clone https://github.com/angeless/opencut.git
cd opencut
pip install -r requirements.txt
```

### 📖 Quick Start

```bash
# Index your video library
python -m opencut.indexer scan --input /path/to/videos --output ./index/

# Create video with one command
python -m opencut.editor create --topic "My Travel Story" --style wanderlust
```

### 🔧 Requirements

- Python 3.8+
- FFmpeg 4.0+
- CUDA (optional, for GPU acceleration)

### 📄 License

MIT License - See [LICENSE](LICENSE)

### 🙏 Acknowledgments

- FFmpeg for video processing
- OpenAI CLIP for semantic understanding
- Faster-Whisper for speech recognition
- GPT-SoVITS for voice cloning
