# 🎬 QuackMedia

**QuackMedia** is the QuackVerse module for working with multimedia assets — including video, audio, and image processing. It provides developer-friendly wrappers around tools like FFmpeg, Whisper, and other media utilities, designed to be used programmatically or as part of a QuackTool.

---

## 📌 Purpose

QuackMedia aims to:
- Expose clean, forkable functions for common media operations
- Simplify complex CLI tools (like FFmpeg) for Python devs
- Empower automation of tasks like clipping, transcoding, transcription, and frame extraction

---

## 📦 Folder Structure

```
src/quackmedia/
├── __init__.py
├── pandoc.py          # File conversion, markdown to html
├── ffmpeg.py          # Video/audio conversion, slicing, compression
├── whisper.py         # Transcription logic (OpenAI Whisper)
├── images.py          # Image utilities (e.g. resizing, extracting frames)
└── plugins.py         # Plugin registry for quackcore
```

---

## 🔌 Plugin Registration

Each integration registers with QuackCore’s plugin registry so that tools and CLI workflows can auto-discover them:

```python
from quackcore.integrations.core import register_plugin

@register_plugin("ffmpeg")
def register_ffmpeg():
    return FFmpegIntegration()
```

---

## 🚀 Example Use

Extract frames from a video using FFmpeg:

```python
from quackmedia.ffmpeg import extract_frames

extract_frames(
    video_path=\"input.mp4\",
    output_folder=\"/tmp/frames\",
    fps=2
)
```

Transcribe audio with Whisper:

```python
from quackmedia.whisper import transcribe_audio

text = transcribe_audio(\"meeting.wav\")
print(text)
```

---

## 🧪 Tests

All tests live in `tests/quackmedia/` and should:
- Use temporary directories for file-based operations
- Mock subprocess calls and model loading where possible
- Avoid reliance on large files or remote resources

---

## 📐 Design Philosophy

QuackMedia functions:
- Should not expose FFmpeg or Whisper internals
- Must be idempotent and callable directly from `tool.py`
- Should prefer `Path` objects over strings for I/O

---

## 🎯 Ideal Use Cases

- Automatically generating social media clips from long videos
- Transcribing podcast episodes or Zoom calls
- Creating thumbnails or animated GIFs from video assets
- Clipping reels, shorts, or course previews for creators

---

## 🛠 Future Ideas

- Image captioning with CLIP
- Thumbnail generation with DALL·E or custom prompts
- Audio cleanup using PyDub, RNNoise, or custom denoisers

---

QuackMedia makes media programmable. 🎥🐣 Whether you're slicing videos, transcribing thoughts, or cooking thumbnails — do it like a duck.