# ✨ StarStitch

**Seamless AI-powered video morphing pipeline that creates continuous "celebrity selfie chain" transitions.**

[![Python 3.x](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version: 0.3](https://img.shields.io/badge/Version-0.3-purple.svg)]()

---

## 🎬 What is StarStitch?

StarStitch is a Python automation tool that generates seamless "morphing selfie" video chains. Give it a list of people (celebrities, team members, historical figures—anyone!) and a location, and it creates a single continuous video where one person appears to morph into the next while maintaining the same selfie angle.

**The Magic:** The end frame of each transition becomes the start frame of the next, creating pixel-perfect continuity that looks like one impossible, continuous shot.

---

## ✨ Key Features

- **Frame-Perfect Transitions** — Extracts the exact last frame of each video segment to ensure zero-glitch morphing
- **Multi-Provider Support** — Choose between Fal.ai (Kling), Runway ML (Gen-3), or Luma AI (Dream Machine)
- **Modern Web UI** — Beautiful Streamlit interface with dark theme and real-time progress
- **CLI & Web Modes** — Run via command line or interactive web interface
- **Crash Recovery** — Resume capability allows picking up where you left off if generation fails mid-sequence
- **JSON Configuration** — Swap subjects and scenes without touching code
- **Extensible Architecture** — Factory pattern makes adding new providers trivial

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        StarStitch Pipeline                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   config.json ──► ImageGenerator ──► VideoGenerator ──► FFMPEG  │
│        │              (Replicate)    (Fal/Runway/Luma)     │     │
│        │                   │                 │             │     │
│        ▼                   ▼                 ▼             ▼     │
│   [Subjects]    →    [Images]    →    [Videos]    →   [Final]   │
│   [Location]         anchor.png       morph_01.mp4    output.mp4│
│                      target_01.png    morph_02.mp4              │
│                      target_02.png    morph_03.mp4              │
│                          ...              ...                    │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  THE "GLITCH FIX" LOOP:                                  │  │
│   │  1. Generate target image                                │  │
│   │  2. Create morph video (start → end)                     │  │
│   │  3. Extract LAST FRAME of video                          │  │
│   │  4. Use extracted frame (not original!) as next start    │  │
│   │  5. Repeat for each subject                              │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎥 Supported Video Providers

| Provider | Model | Best For |
|----------|-------|----------|
| **Fal.ai** | Kling v1.6 Pro | High-quality morphing, reliable output |
| **Runway ML** | Gen-3 Alpha Turbo | Fast generation, cinematic quality |
| **Luma AI** | Dream Machine | Smooth transitions, photorealistic |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- FFMPEG installed and available in PATH
- API keys for your chosen providers

### Installation

```bash
# Clone the repository
git clone https://github.com/scott29kelly/StarStitch.git
cd StarStitch

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Configuration

Create or edit `config.json`:

```json
{
  "project_name": "my_first_stitch",
  "output_folder": "renders",
  "settings": {
    "aspect_ratio": "9:16",
    "transition_duration": "5",
    "video_provider": "fal",
    "image_model": "black-forest-labs/flux-1.1-pro",
    "video_model": "fal-ai/kling-video/v1.6/pro/image-to-video"
  },
  "global_scene": {
    "location_prompt": "taking a selfie at the Eiffel Tower, golden hour lighting, 4k photorealistic",
    "negative_prompt": "blurry, distorted, cartoon, low quality"
  },
  "sequence": [
    {
      "id": "anchor",
      "name": "Tourist",
      "visual_prompt": "A friendly tourist in casual clothes, smiling broadly"
    },
    {
      "id": "celeb_01",
      "name": "Elon Musk",
      "visual_prompt": "Elon Musk in a black t-shirt, slight smirk"
    },
    {
      "id": "celeb_02",
      "name": "Taylor Swift",
      "visual_prompt": "Taylor Swift with red lipstick, genuine smile"
    }
  ]
}
```

### Run

**Command Line Interface:**

```bash
python main.py

# Or with a specific config file
python main.py --config my_custom_config.json

# Resume a crashed render
python main.py --resume renders/render_20250117_143022

# Dry run (validate config without API calls)
python main.py --dry-run
```

**Web UI:**

```bash
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

---

## 📁 Project Structure

```
StarStitch/
├── main.py                         # CLI entry point with crash recovery
├── app.py                          # Streamlit Web UI
├── config.py                       # Configuration loader & validation
├── config.json                     # Default configuration
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
├── providers/
│   ├── __init__.py                 # Package exports
│   ├── base_provider.py            # Abstract base for all providers
│   ├── base_video_generator.py     # Abstract base for video providers
│   ├── image_generator.py          # Replicate/Flux wrapper
│   ├── fal_video_generator.py      # Fal.ai/Kling implementation
│   ├── runway_generator.py         # Runway ML Gen-3 implementation
│   ├── luma_generator.py           # Luma Dream Machine implementation
│   ├── video_generator.py          # Backward compatibility exports
│   └── video_provider_factory.py   # Factory pattern for provider selection
├── utils/
│   ├── __init__.py
│   ├── ffmpeg_utils.py             # Frame extraction & concatenation
│   ├── file_manager.py             # Asset organization & paths
│   └── state_manager.py            # Pipeline state & resume logic
└── renders/                        # Output directory (generated)
    └── render_{timestamp}/
        ├── 00_anchor.png
        ├── 01_target.png
        ├── 01_morph.mp4
        ├── 01_lastframe.png
        ├── ...
        └── final_starstitch.mp4
```

---

## 🔑 Environment Variables

Create a `.env` file with your API keys:

```bash
# Image Generation (Required)
REPLICATE_API_TOKEN=your_replicate_token

# Video Providers (Configure the one you use)
FAL_KEY=your_fal_key              # For Fal.ai/Kling
RUNWAY_API_KEY=your_runway_key    # For Runway ML
LUMA_API_KEY=your_luma_key        # For Luma AI
```

---

## 🔧 Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Language** | Python 3.x | Core application |
| **Image Gen** | Replicate (Flux 1.1 Pro) | High-quality image generation |
| **Video Gen** | Fal.ai / Runway / Luma | Start/end frame morphing |
| **Video Processing** | FFMPEG | Frame extraction & concatenation |
| **Web UI** | Streamlit | Interactive configuration & monitoring |
| **Config** | JSON | Flexible scene definition |

---

## 🎯 Use Cases

- **Social Media Content** — Eye-catching morphing reels for TikTok/Instagram
- **Team Introductions** — Fun "meet the team" videos for organizations
- **Event Promotion** — Morph through speakers/performers at an event
- **Historical Timelines** — Morph through historical figures at famous locations
- **Creative Projects** — Artistic video experiments and music videos

---

## 🗺️ Roadmap

- [x] **v0.1** — Core pipeline with Replicate + Fal.ai integration
- [x] **v0.2** — Web UI for configuration (Streamlit)
- [x] **v0.3** — Additional video providers (Runway, Luma)
- [ ] **v0.4** — Audio track integration
- [ ] **v0.5** — Batch processing for multiple configs
- [ ] **v1.0** — Production-ready release with comprehensive error handling

---

## 🧩 Adding New Providers

The factory pattern makes adding new video providers simple:

```python
from providers.base_video_generator import BaseVideoGenerator
from providers.video_provider_factory import VideoProviderFactory

class MyVideoGenerator(BaseVideoGenerator):
    PROVIDER_ID = "myprovider"
    
    @property
    def provider_name(self) -> str:
        return "My Provider"
    
    def generate(self, start_image_path, end_image_path, output_path, ...):
        # Implementation here
        pass

# Register the provider
VideoProviderFactory.register("myprovider", MyVideoGenerator)
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Replicate](https://replicate.com/) for accessible AI model APIs
- [Fal.ai](https://fal.ai/) for Kling video generation endpoints
- [Runway ML](https://runwayml.com/) for Gen-3 video generation
- [Luma AI](https://lumalabs.ai/) for Dream Machine
- [Black Forest Labs](https://blackforestlabs.ai/) for the Flux image model

---

## ⚠️ Disclaimer

This tool generates AI content. Please use responsibly and in accordance with:
- The terms of service of all API providers
- Copyright and likeness rights considerations
- Platform content policies where you share the output

**Note:** Generated content featuring real people should be clearly labeled as AI-generated and used only for legitimate creative purposes.

---

<p align="center">
  <strong>Built with 🤖 + ☕ by <a href="https://github.com/scott29kelly">Scott Kelly</a></strong>
</p>
