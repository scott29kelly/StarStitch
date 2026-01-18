# 🌟 StarStitch

**Seamless AI-powered video morphing pipeline that creates continuous "celebrity selfie chain" transitions.**

[![Python 3.x](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status: In Development](https://img.shields.io/badge/Status-In%20Development-yellow.svg)]()

---

## 🎬 What is StarStitch?

StarStitch is a Python automation tool that generates seamless "morphing selfie" video chains. Give it a list of people (celebrities, team members, historical figures—anyone!) and a location, and it creates a single continuous video where one person appears to morph into the next while maintaining the same selfie angle.

**The Magic:** The end frame of each transition becomes the start frame of the next, creating pixel-perfect continuity that looks like one impossible, continuous shot.

---

## ✨ Key Features

- **Frame-Perfect Transitions** — Extracts the exact last frame of each video segment to ensure zero-glitch morphing
- **Dual-Provider Architecture** — Leverages Replicate for fast image generation and Fal.ai for high-quality video morphing
- **Multi-Provider Support** — Choose from Fal.ai (Kling), Runway ML Gen-3, or Luma Dream Machine for video generation
- **Audio Integration** — Add background music with volume control, fade effects, and automatic looping
- **Batch Processing** — Process multiple config files in a directory with summary reports and resume capability
- **Template System** — Pre-built scene templates for viral, holiday, event, and themed content
- **Output Variants** — Generate multiple aspect ratios (9:16, 16:9, 1:1) from a single render
- **Web UI** — Modern Streamlit interface for visual configuration (no JSON editing required)
- **Crash Recovery** — Resume capability allows picking up where you left off if generation fails mid-sequence
- **JSON Configuration** — Swap subjects and scenes without touching code
- **Modular Design** — Easily swap AI providers as APIs evolve
- **Modern Web UI** — Beautiful 2026-standard interface with glassmorphism, animations, and intuitive workflows

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        StarStitch Pipeline                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   config.json ──► ImageGenerator ──► VideoGenerator ──► FFMPEG  │
│        │              (Replicate)       (Fal.ai/Kling)     │     │
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

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- FFMPEG installed and available in PATH
- API keys for [Replicate](https://replicate.com/) and [Fal.ai](https://fal.ai/)

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

### Option 1: Web UI (Recommended)

```bash
# Launch the Streamlit web interface
streamlit run app.py
```

The Web UI provides:
- Visual sequence builder with drag-and-drop reordering
- Scene presets for popular locations
- Real-time cost and time estimates
- JSON export for CLI usage

### Option 2: CLI

Create or edit `config.json`:

```json
{
  "project_name": "my_first_stitch",
  "output_folder": "renders",
  "settings": {
    "aspect_ratio": "9:16",
    "transition_duration_sec": 5,
    "image_model": "black-forest-labs/flux-1.1-pro",
    "video_model": "fal-ai/kling-video/v1.6/pro/image-to-video"
  },
  "global_scene": {
    "location_prompt": "taking a selfie at the Eiffel Tower, golden hour lighting, 4k photorealistic",
    "negative_prompt": "blurry, distorted, cartoon, low quality"
  },
  "audio": {
    "enabled": true,
    "audio_path": "/path/to/background-music.mp3",
    "volume": 0.8,
    "fade_in_sec": 1.0,
    "fade_out_sec": 2.0,
    "loop": true,
    "normalize": true
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

Then run:

```bash
python main.py

# Or with a specific config file
python main.py --config my_custom_config.json

# Resume a crashed render
python main.py --resume renders/render_20250117_143022

# Use a template
python main.py --template tiktok_celeb_morph

# List available templates
python main.py --list-templates

# Generate multiple aspect ratio variants
python main.py --variants 16:9,1:1

# Process multiple configs in a batch
python main.py --batch ./batch_configs/
```

---

## 🖥️ Web UI

StarStitch includes a modern, minimal web interface built with Streamlit.

### Features

| Tab | Description |
|-----|-------------|
| **Templates** | Browse pre-built templates for viral, holiday, event, and themed content |
| **Sequence** | Add, remove, and reorder subjects in your morph chain |
| **Scene** | Configure location prompts and quality settings |
| **Audio** | Upload background music, set volume, fade effects, and looping |
| **Variants** | Generate multiple aspect ratio versions (9:16, 16:9, 1:1) |
| **Preview** | Review your configuration and see estimates |
| **Generate** | Pre-flight checks and pipeline execution |

### Screenshots

The UI features:
- Dark theme with violet accent colors
- Real-time cost/time estimates
- Pre-flight API key validation
- JSON export for reproducibility

---

## 📁 Project Structure

```
StarStitch/
├── main.py                 # CLI entry point and ChainManager
├── app.py                  # Streamlit Web UI
├── config.py               # Configuration loader & dataclasses
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── config.json             # Default configuration
├── providers/
│   ├── __init__.py
│   ├── image_generator.py  # Replicate wrapper
│   ├── video_generator.py  # Fal.ai wrapper
│   └── video_provider_factory.py  # Provider factory pattern
├── utils/
│   ├── __init__.py
│   ├── ffmpeg_utils.py     # Frame extraction, concatenation & variants
│   ├── audio_utils.py      # Audio processing & merging
│   ├── file_manager.py     # Asset organization & resume logic
│   ├── batch_processor.py  # Batch processing manager
│   └── template_loader.py  # Template system loader
├── templates/              # Pre-built scene templates
│   ├── viral/              # TikTok, Reels trends
│   ├── holidays/           # Christmas, Halloween, etc.
│   ├── events/             # Birthday, Wedding, Graduation
│   └── themes/             # Travel, Nature, Fantasy
├── web/                    # React Web UI
│   ├── src/
│   │   ├── components/     # UI components
│   │   ├── hooks/          # Custom React hooks
│   │   ├── App.tsx         # Main application
│   │   ├── index.css       # Design system & styles
│   │   └── types.ts        # TypeScript definitions
│   ├── package.json
│   └── vite.config.ts
└── renders/                # Output directory (generated)
    └── render_{timestamp}/
        ├── manifest.json       # Resume state
        ├── config.json         # Render config
        ├── 00_anchor.png
        ├── 01_target.png
        ├── 01_morph.mp4
        ├── 01_lastframe.png
        ├── variants/           # Aspect ratio variants
        │   ├── final_starstitch_16x9.mp4
        │   └── final_starstitch_1x1.mp4
        └── final_starstitch.mp4
```

---

## 🔧 Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Language** | Python 3.x | Core application |
| **Image Gen** | Replicate (Flux 1.1 Pro) | High-quality celebrity likeness |
| **Video Gen** | Fal.ai (Kling v1.6 Pro) | Start/end frame morphing |
| **Video Processing** | FFMPEG | Frame extraction & concatenation |
| **Web UI** | Streamlit | Visual configuration interface |
| **Config** | JSON | Flexible scene definition |

---

## 🎯 Use Cases

- **Social Media Content** — Eye-catching morphing reels for TikTok/Instagram
- **Team Introductions** — Fun "meet the team" videos for organizations
- **Event Promotion** — Morph through speakers/performers at an event
- **Historical Timelines** — Morph through historical figures at famous locations
- **Creative Projects** — Artistic video experiments and music videos

---

## 🌐 Web UI

StarStitch now includes a beautiful, modern web interface built with cutting-edge 2026 design standards.

### Features

- **Glassmorphism Design** — Frosted glass cards with subtle depth and shadows
- **Bento Grid Dashboard** — Modern card-based layout with stats and quick actions
- **Drag-Drop Sequence Builder** — Intuitive subject ordering with visual feedback
- **Multi-Step Configuration** — Wizard-style flow for project setup
- **Real-Time Render Progress** — Animated circular progress with step tracking
- **Toast Notifications** — Elegant feedback for all actions
- **Responsive Layout** — Works beautifully on all screen sizes

### Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | React 18 + TypeScript |
| Build Tool | Vite |
| Styling | Tailwind CSS v4 |
| Animations | Framer Motion |
| Drag & Drop | @dnd-kit |
| Icons | Lucide React |

### Running the Web UI

```bash
cd web
npm install
npm run dev
```

Visit `http://localhost:5173` to see the interface.

### Design Highlights

- **Color Palette**: Deep space void with cosmic aurora gradients (indigo → purple → pink)
- **Typography**: Inter for UI, JetBrains Mono for code
- **Animations**: Spring-based micro-interactions with 60fps performance
- **Accessibility**: Focus rings, keyboard navigation, semantic HTML

---

## 🗺️ Roadmap

- [x] **v0.1** — Core pipeline with Replicate + Fal.ai integration
- [x] **v0.2** — Web UI for configuration (Streamlit + React)
- [x] **v0.3** — Additional video providers (Runway ML, Luma AI) with factory pattern
- [x] **v0.4** — Audio track integration (volume, fades, looping, normalization)
- [x] **v0.5** — Batch processing, templates, and output variants
- [ ] **v0.6** — FastAPI backend with WebSocket progress updates
- [ ] **v1.0** — Production-ready release with comprehensive error handling

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
- [Black Forest Labs](https://blackforestlabs.ai/) for the Flux image model
- [Streamlit](https://streamlit.io/) for the web UI framework
- The AI coding community for vibe coding inspiration

---

## ⚠️ Disclaimer

This tool generates AI content. Please use responsibly and in accordance with:
- The terms of service of Replicate and Fal.ai
- Copyright and likeness rights considerations
- Platform content policies where you share the output

**Note:** Generated content featuring real people should be clearly labeled as AI-generated and used only for legitimate creative purposes.

---

<p align="center">
  <strong>Built with 🤖 + ☕ by <a href="https://github.com/scott29kelly">Scott Kelly</a></strong>
</p>
