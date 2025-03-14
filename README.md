# 🦆 QuackVideo

## AI-Powered Video Processing for Educational Content

QuackVideo is a powerful video processing tool designed for educational content creators. It automates video editing, clip extraction, and post-production to help you create professional content for multiple platforms from a single recording.

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![QuackCore](https://img.shields.io/badge/QuackCore-Compatible-green.svg)](https://github.com/rodmtech/quackcore)

## 🎥 Features

- **Automated Video Editing**: Post-process recordings with noise reduction, color correction, and audio normalization
- **Smart Clip Extraction**: Identify and extract key moments for social media sharing
- **Multi-platform Export**: Format content for YouTube, Instagram, TikTok, LinkedIn, and more
- **Content Analysis**: Identify key topics, chapter markers, and highlights
- **Transition Generation**: Create professional transitions between segments
- **Thumbnail Extraction**: Pull the best frames for thumbnail creation
- **B-Roll Management**: Extract and organize segments for b-roll footage
- **Caption Generation**: Create accurate captions and subtitles
- **Format Conversion**: Convert between video formats while maintaining quality

## 🚀 Installation

```bash
# Install from PyPI
pip install quackvideo

# Or install from source
git clone https://github.com/rodmtech/quackvideo.git
cd quackvideo
pip install -e .
```

## 📋 Requirements

- Python 3.13+
- FFmpeg 5.0+
- QuackCore library
- Anthropic API key (optional, for enhanced analysis)

## 🧩 Integrations

QuackVideo is part of the QuackVerse ecosystem and integrates with:

- **QuackCore**: Provides infrastructure and shared utilities
- **QuackBuddy**: Orchestration and command-line interface
- **QuackImage**: For thumbnail generation from extracted frames
- **QuackDistro**: For text content generated from video transcripts
- **AI Product Engineer**: Final publication destination

## 💻 Quick Start

```bash
# Process a video with default settings
quackvideo process my-recording.mp4 --output processed/

# Extract short clips for social media
quackvideo extract-clips my-recording.mp4 --duration 60 --count 3

# Create a highlights compilation
quackvideo create-highlights my-recording.mp4 --duration 5:00

# Run through QuackBuddy
quackbuddy video process my-recording.mp4
```

## 🔍 Example: Process a Tutorial Video

```python
from quackvideo.processor import VideoProcessor
from quackvideo.analysis import ContentAnalyzer
from quackvideo.export import ClipExporter

# Initialize processor
processor = VideoProcessor()

# Process the main video
processed_video = processor.process(
    "python_tutorial.mp4",
    normalize_audio=True,
    enhance_video=True,
    reduce_noise=True
)

# Analyze content for key moments
analyzer = ContentAnalyzer()
key_moments = analyzer.find_key_moments(processed_video, count=5)

# Export clips for different platforms
exporter = ClipExporter()
for i, moment in enumerate(key_moments):
    # Create Twitter/X clip
    exporter.create_clip(
        processed_video,
        start=moment.start_time,
        duration=60,
        output=f"clips/twitter_clip_{i}.mp4",
        format="twitter"
    )
    
    # Create TikTok clip
    exporter.create_clip(
        processed_video,
        start=moment.start_time,
        duration=60,
        output=f"clips/tiktok_clip_{i}.mp4",
        format="tiktok",
        add_captions=True
    )
```

## 📊 Workflow Architecture

```
Recording → Preprocessing → Content Analysis → Editing → Platform-Specific Export
    ↓             ↓                 ↓             ↓               ↓
 Quality      Background        Topic/Segment   Transition    Format/Resolution
Enhancement   Removal           Detection       Generation     Optimization
    ↓             ↓                 ↓             ↓               ↓
 Audio        Color              Key Moment     Visual        Platform-Specific
Normalization Correction         Detection      Effects        Metadata
```

## 📝 Example Configuration

```yaml
# quackvideo.yaml
projects:
  python_tutorials:
    output_path: "/media/tutorials/python"
    preferred_resolution: "1080p"
    platforms:
      - youtube
      - twitter
      - linkedin
    clip_duration: 60
    highlight_count: 5
    
processing:
  audio:
    normalize: true
    noise_reduction: 0.2
    compression: true
  video:
    color_correction: true
    stabilization: false
    
platforms:
  youtube:
    resolution: "1080p"
    aspect_ratio: "16:9"
    format: "mp4"
  twitter:
    resolution: "720p"
    aspect_ratio: "16:9"
    format: "mp4"
    max_duration: 140
  tiktok:
    resolution: "1080p"
    aspect_ratio: "9:16"
    format: "mp4"
    max_duration: 180
```

## 🔧 Command-Line Interface

QuackVideo provides a comprehensive CLI:

```
Usage: quackvideo [OPTIONS] COMMAND [ARGS]...

Options:
  --config PATH  Path to configuration file
  --verbose      Enable verbose output
  --help         Show this message and exit

Commands:
  process          Process a full video
  extract-frames   Extract frames from video
  extract-clips    Extract short clips from video
  create-highlights  Create a highlights compilation
  analyze-content   Analyze video content
  generate-captions Generate captions/subtitles
  convert           Convert video to different format
```

## 📚 Documentation

Full documentation is available at [https://rodmtech.github.io/quackvideo/](https://rodmtech.github.io/quackvideo/)

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=quackvideo
```

## 🔄 Contributing

Contributions are welcome! Please check out our [contribution guidelines](CONTRIBUTING.md) for details.

## 🔗 Related Projects

- [QuackCore](https://github.com/rodmtech/quackcore) - Core infrastructure
- [QuackBuddy](https://github.com/rodmtech/quackbuddy) - Orchestration layer
- [QuackImage](https://github.com/rodmtech/quackimage) - Image generation
- [QuackDistro](https://github.com/rodmtech/quackdistro) - Content distribution
- [QuackResearch](https://github.com/rodmtech/quackresearch) - Research and planning
- [QuackTutorial](https://github.com/rodmtech/quacktutorial) - Tutorial generation

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- Built with [QuackCore](https://github.com/rodmtech/quackcore)
- Powered by [FFmpeg](https://ffmpeg.org/) and [OpenCV](https://opencv.org/)
- AI capabilities provided by [Anthropic Claude](https://www.anthropic.com/claude)
