# StarStitch Roadmap

## Completed

### v0.1 - Core Pipeline ✅
- Replicate (Flux) integration for image generation
- Fal.ai (Kling) integration for video morphing
- FFMPEG frame extraction for seamless transitions
- JSON configuration system
- CLI entry point with crash recovery

### v0.2 - Web UI ✅
- Streamlit Web UI with dark theme
- Visual sequence builder
- Scene presets
- Real-time cost/time estimates
- React frontend (web/) with modern glassmorphism design

### v0.3 - Multi-Provider Support ✅
- Factory pattern for video providers
- Fal.ai (Kling v1.5/v1.6)
- Runway ML Gen-3 Alpha
- Luma AI Dream Machine
- Provider selection in config

### v0.4 - Audio Track Integration ✅
- Background music support
- Volume control (0-100%)
- Fade in/out effects
- Auto-loop for short audio
- EBU R128 loudness normalization
- Audio tab in Web UI

### v0.5 - Batch Processing & Templates ✅
- **Batch Configuration**
  - Accept directory of config files (`--batch` CLI flag)
  - Sequential processing with summary report
  - Skip already-completed renders
  - Graceful interruption with resume capability
  - Manifest-based progress tracking

- **Template System**
  - Pre-built scene templates in `templates/` folder
  - Categories: viral, holidays, events, themes (12+ templates)
  - `--template` flag to use templates
  - `--list-templates` to view available templates
  - Template browser in Web UI with search and filtering

- **Queue Manager**
  - Batch progress tracking in manifest
  - Estimated completion times based on historical averages
  - Graceful interruption with SIGINT/SIGTERM handling
  - Resume capability for interrupted batches

- **Output Variants**
  - Generate multiple aspect ratios from single run
  - Formats: 9:16, 16:9, 1:1, 4:5, 4:3, 3:4
  - `--variants` CLI flag
  - FFMPEG-based intelligent cropping (center-focused)
  - Variants tab in Web UI

---

## In Progress

### v0.6 - API Backend
**Goal:** RESTful API for programmatic access and React frontend integration

- [ ] **FastAPI Server**
  - `POST /api/render` - Start new render
  - `GET /api/render/{id}` - Get render status
  - `DELETE /api/render/{id}` - Cancel render
  - `GET /api/renders` - List all renders
  - `GET /api/templates` - List available templates

- [ ] **WebSocket Progress**
  - Real-time render updates
  - Step-by-step progress streaming
  - Error notifications

- [ ] **Job Queue**
  - Redis for job storage
  - Celery for background workers
  - Configurable concurrency

- [ ] **React Frontend Integration**
  - Connect existing `web/` to FastAPI backend
  - Real-time progress updates
  - Render history view

---

### v0.7 - Cloud Storage & Sharing
**Goal:** Store and share renders in the cloud

- [ ] **Cloud Upload**
  - S3/Cloudflare R2 integration
  - Auto-upload on completion
  - Configurable bucket/path

- [ ] **Shareable Links**
  - Generate public URLs
  - Optional expiration
  - Password protection option

- [ ] **Gallery View**
  - Browse past renders
  - Video thumbnails
  - Filter by date/project

- [ ] **Social Export**
  - Direct post to TikTok (via API)
  - Instagram Reels integration
  - YouTube Shorts upload

---

### v0.8 - Advanced Video Features
**Goal:** Enhanced video effects and customization

- [ ] **Custom Transitions**
  - Crossfade between morphs
  - Zoom/pan effects
  - Glitch/VHS effects
  - Configurable per-transition

- [ ] **Watermark/Overlay**
  - Logo placement (corner positions)
  - Text overlays
  - Animated watermarks

- [ ] **Caption Generation**
  - Auto-generate subject names
  - Customizable font/style
  - SRT export

- [ ] **Speed Ramping**
  - Slow-motion segments
  - Speed-up effects
  - Configurable timing curves

---

### v0.9 - Quality & Polish
**Goal:** Production-grade reliability and observability

- [ ] **Unit Tests**
  - pytest coverage for core modules
  - Mock API responses for testing
  - CI/CD integration

- [ ] **Error Recovery**
  - Exponential backoff for API failures
  - Automatic retry with configurable limits
  - Graceful degradation

- [ ] **Cost Tracking**
  - Log API spend per render
  - Cost breakdown by provider
  - Budget alerts

- [ ] **Logging Dashboard**
  - Structured JSON logs
  - Log aggregation
  - Filtering and search

---

### v1.0 - Production Release
**Goal:** Ready for public use

- [ ] **Docker Container**
  - Single-command deployment
  - Docker Compose for full stack
  - Environment variable configuration

- [ ] **Environment Validation**
  - Startup dependency checks
  - API key validation
  - FFMPEG version check

- [ ] **Documentation Site**
  - Full API documentation
  - Tutorial guides
  - Example gallery

- [ ] **Demo Video**
  - Showcase reel
  - Feature walkthrough
  - README embedded

---

## Future Ideas (Backlog)

- **Face Detection** - Auto-detect faces for better framing
- **Style Transfer** - Apply artistic styles to morphs
- **Multi-Language** - i18n support for Web UI
- **Mobile App** - React Native companion app
- **Webhook Notifications** - POST to custom endpoint on completion
- **Team Collaboration** - Shared projects and render history
- **AI Prompt Enhancement** - Auto-improve visual prompts
- **Scheduled Renders** - Cron-style scheduling
