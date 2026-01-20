"""
StarStitch Web UI
A modern interface for configuring AI-powered video morphing sequences.
"""

import streamlit as st
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import uuid
from dotenv import load_dotenv

# Load environment variables from .env.local or .env
load_dotenv(".env.local")
load_dotenv(".env")  # Fallback to .env if .env.local doesn't exist

import time
from utils import TemplateLoader, Template, BatchProcessor, BatchSummary
from utils import PipelineRunner, PipelineProgress, PipelineStatus

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="StarStitch",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# CUSTOM STYLING - Intentional Minimalism
# =============================================================================

st.markdown("""
<style>
    /* ============================================================
       StarStitch Design System - Aligned with React Frontend
       ============================================================ */

    /* Font imports */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Root variables - Deep Space Theme */
    :root {
        /* Background layers */
        --void: #050507;
        --obsidian: #0a0a0f;
        --slate: #12121a;
        --ash: #1a1a24;
        --smoke: #252532;
        --mist: #3a3a4a;

        /* Text hierarchy */
        --snow: #f0f0f8;
        --cloud: #c8c8d8;
        --silver: #8888a0;

        /* Aurora gradient */
        --aurora-start: #6366f1;
        --aurora-mid: #a855f7;
        --aurora-end: #ec4899;

        /* Neon accents */
        --neon-cyan: #22d3ee;
        --neon-emerald: #34d399;

        /* Semantic */
        --success: #22c55e;
        --warning: #f59e0b;
        --error: #ef4444;

        /* Computed */
        --accent: var(--aurora-mid);
        --accent-hover: #b97afc;
        --border: var(--mist);
        --border-subtle: rgba(136, 136, 160, 0.15);
    }

    /* Global app styling */
    .stApp {
        background: var(--obsidian) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        -webkit-font-smoothing: antialiased;
    }

    /* Base text styling */
    .stApp, .stApp p, .stApp span, .stApp div {
        color: var(--cloud);
        font-size: 15px;
        line-height: 1.6;
    }

    /* Hide default Streamlit elements */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}

    /* Typography */
    h1, h2, h3, h4, h5 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em !important;
        color: var(--snow) !important;
    }

    h1 { font-size: 1.875rem !important; }
    h2 { font-size: 1.5rem !important; }
    h3 { font-size: 1.25rem !important; }
    h4 { font-size: 1.0625rem !important; }
    h5 { font-size: 1rem !important; }

    /* Markdown text */
    .stMarkdown, .stMarkdown p {
        color: var(--cloud) !important;
    }

    /* ============================================================
       Sidebar
       ============================================================ */
    section[data-testid="stSidebar"] {
        background: var(--slate) !important;
        border-right: 1px solid var(--border-subtle) !important;
    }

    section[data-testid="stSidebar"] .stMarkdown p {
        color: var(--cloud) !important;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4 {
        color: var(--snow) !important;
    }

    /* ============================================================
       Glassmorphic Components
       ============================================================ */

    /* Expanders */
    .stExpander {
        background: rgba(26, 26, 36, 0.6) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 16px !important;
    }

    .stExpander:hover {
        border-color: rgba(136, 136, 160, 0.25) !important;
    }

    /* Container borders */
    [data-testid="stVerticalBlock"] > div:has(> .stExpander) {
        border-radius: 16px;
    }

    /* ============================================================
       Input Fields
       ============================================================ */
    .stTextInput input,
    .stTextArea textarea,
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background: var(--smoke) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 10px !important;
        color: var(--snow) !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 15px !important;
        padding: 0.625rem 0.875rem !important;
    }

    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: var(--silver) !important;
    }

    .stTextInput input:focus,
    .stTextArea textarea:focus,
    .stSelectbox > div > div:focus-within {
        border-color: var(--aurora-mid) !important;
        box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.2), 0 0 20px rgba(168, 85, 247, 0.1) !important;
        outline: none !important;
    }

    /* Labels */
    .stTextInput label,
    .stTextArea label,
    .stSelectbox label,
    .stSlider label,
    .stCheckbox label,
    .stRadio label {
        color: var(--cloud) !important;
        font-size: 0.9375rem !important;
        font-weight: 500 !important;
    }

    /* ============================================================
       Buttons
       ============================================================ */
    .stButton > button {
        background: linear-gradient(135deg, var(--aurora-start), var(--aurora-mid)) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.9375rem !important;
        padding: 0.625rem 1.5rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25) !important;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, var(--aurora-mid), var(--aurora-end)) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(168, 85, 247, 0.35) !important;
    }

    .stButton > button:active {
        transform: translateY(0) !important;
    }

    .stButton > button:disabled {
        background: var(--smoke) !important;
        color: var(--silver) !important;
        box-shadow: none !important;
        cursor: not-allowed !important;
    }

    /* Secondary/outline buttons (using container styling) */
    .stButton > button[kind="secondary"],
    [data-testid="baseButton-secondary"] {
        background: transparent !important;
        border: 1px solid var(--border) !important;
        color: var(--cloud) !important;
        box-shadow: none !important;
    }

    [data-testid="baseButton-secondary"]:hover {
        background: var(--smoke) !important;
        border-color: var(--silver) !important;
    }

    /* ============================================================
       Sliders & Progress
       ============================================================ */
    .stSlider > div > div > div {
        background: linear-gradient(90deg, var(--aurora-start), var(--aurora-mid)) !important;
    }

    .stSlider > div > div > div > div {
        background: var(--snow) !important;
        border: 2px solid var(--aurora-mid) !important;
    }

    .stProgress > div > div {
        background: linear-gradient(90deg, var(--aurora-start), var(--aurora-mid)) !important;
    }

    /* ============================================================
       Tabs
       ============================================================ */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--slate) !important;
        border-radius: 12px !important;
        padding: 4px !important;
        gap: 4px !important;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: var(--silver) !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 500 !important;
    }

    .stTabs [aria-selected="true"] {
        background: var(--ash) !important;
        color: var(--snow) !important;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        background: transparent !important;
    }

    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }

    /* ============================================================
       Custom Components
       ============================================================ */

    /* Glass card */
    .glass-card {
        background: rgba(26, 26, 36, 0.6);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--border-subtle);
        border-radius: 16px;
        padding: 1.5rem;
        transition: all 0.2s ease;
    }

    .glass-card:hover {
        border-color: rgba(136, 136, 160, 0.25);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }

    /* Subject card */
    .subject-card {
        background: var(--ash);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        transition: all 0.2s ease;
    }

    .subject-card:hover {
        border-color: rgba(136, 136, 160, 0.3);
    }

    .subject-card.anchor {
        border-left: 3px solid var(--aurora-mid);
    }

    /* Status badges */
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.3rem 0.875rem;
        border-radius: 9999px;
        font-size: 0.8125rem;
        font-weight: 500;
    }

    .status-pending {
        background: rgba(136, 136, 160, 0.2);
        color: var(--silver);
    }

    .status-processing {
        background: rgba(168, 85, 247, 0.25);
        color: var(--aurora-mid);
    }

    .status-complete {
        background: rgba(34, 197, 94, 0.25);
        color: var(--success);
    }

    .status-error {
        background: rgba(239, 68, 68, 0.25);
        color: var(--error);
    }

    /* Header styling */
    .header-container {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 2rem;
        padding-bottom: 1.5rem;
        border-bottom: 1px solid var(--border-subtle);
    }

    .header-logo {
        font-size: 2.5rem;
        line-height: 1;
    }

    .header-title {
        font-size: 1.875rem;
        font-weight: 700;
        color: var(--snow);
        margin: 0;
        background: linear-gradient(135deg, var(--snow), var(--cloud));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .header-subtitle {
        font-size: 0.9375rem;
        color: var(--silver);
        margin: 0;
    }

    /* Metric cards */
    .metric-card {
        background: var(--ash);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
    }

    .metric-value {
        font-size: 1.75rem;
        font-weight: 600;
        color: var(--snow);
        font-family: 'Inter', sans-serif;
    }

    .metric-label {
        font-size: 0.8125rem;
        color: var(--silver);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.25rem;
    }

    /* JSON preview */
    .json-preview {
        background: var(--slate);
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        padding: 1rem;
        font-family: 'JetBrains Mono', 'SF Mono', monospace;
        font-size: 0.875rem;
        color: var(--cloud);
        overflow-x: auto;
    }

    /* Empty state */
    .empty-state {
        text-align: center;
        padding: 3rem 2rem;
        color: var(--silver);
    }

    .empty-state-icon {
        font-size: 3.5rem;
        margin-bottom: 1rem;
        opacity: 0.6;
    }

    .empty-state p {
        font-size: 1rem;
        color: var(--cloud);
        margin: 0.5rem 0;
    }

    .empty-state p:last-child {
        font-size: 0.875rem;
        color: var(--silver);
    }

    /* Info/alert boxes */
    .info-box {
        background: rgba(99, 102, 241, 0.15);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 10px;
        padding: 1rem;
        color: var(--cloud);
    }

    .success-box {
        background: rgba(34, 197, 94, 0.15);
        border: 1px solid rgba(34, 197, 94, 0.3);
        border-radius: 10px;
        padding: 1rem;
    }

    /* Divider */
    .section-divider {
        height: 1px;
        background: var(--border-subtle);
        margin: 2rem 0;
    }

    /* Streamlit native divider */
    hr {
        border-color: var(--border-subtle) !important;
    }

    /* ============================================================
       Animations
       ============================================================ */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    .processing {
        animation: pulse 2s ease-in-out infinite;
    }

    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }

    .shimmer {
        background: linear-gradient(90deg, var(--ash) 25%, var(--smoke) 50%, var(--ash) 75%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
    }

    /* ============================================================
       Streamlit Component Overrides
       ============================================================ */

    /* File uploader */
    .stFileUploader {
        background: var(--smoke) !important;
        border: 1px dashed var(--border) !important;
        border-radius: 10px !important;
    }

    /* Checkbox */
    .stCheckbox > label > span {
        color: var(--cloud) !important;
    }

    /* Toggle */
    [data-testid="stToggle"] span {
        color: var(--cloud) !important;
    }

    /* Metric delta */
    [data-testid="stMetricDelta"] {
        color: var(--cloud) !important;
    }

    /* Info/warning/error boxes */
    .stAlert {
        background: var(--ash) !important;
        border-radius: 10px !important;
    }

    /* Code blocks */
    .stCodeBlock {
        background: var(--slate) !important;
        border-radius: 10px !important;
    }

    code {
        font-family: 'JetBrains Mono', monospace !important;
        background: var(--smoke) !important;
        color: var(--neon-cyan) !important;
        padding: 0.125rem 0.375rem !important;
        border-radius: 4px !important;
    }

    /* Download button */
    .stDownloadButton > button {
        background: var(--smoke) !important;
        border: 1px solid var(--border) !important;
        color: var(--cloud) !important;
        box-shadow: none !important;
    }

    .stDownloadButton > button:hover {
        background: var(--ash) !important;
        border-color: var(--silver) !important;
    }

    /* Container borders */
    [data-testid="stHorizontalBlock"] {
        gap: 1rem;
    }

    /* Captions */
    .stCaption {
        color: var(--silver) !important;
        font-size: 0.8125rem !important;
    }

    /* Constrain video player - 55vh is standard for media players with UI chrome */
    .stVideo {
        max-height: 55vh !important;
        margin-bottom: 1rem;
    }
    .stVideo video {
        max-height: 55vh !important;
        width: auto !important;
        margin: 0 auto;
        display: block;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """Initialize session state with default values."""
    defaults = {
        "project_name": "untitled_stitch",
        "output_folder": "renders",
        "aspect_ratio": "9:16",
        "transition_duration": 5,
        "image_model": "black-forest-labs/flux-1.1-pro",
        "video_provider": "replicate",  # "replicate" (Veo 3.1 Fast ~1min), "fal" (Kling, slow)
        "video_model": "",  # Optional model override
        "location_prompt": "taking a selfie at the Eiffel Tower, golden hour lighting, 4k photorealistic",
        "negative_prompt": "blurry, distorted, cartoon, low quality",
        "sequence": [
            {
                "id": "anchor",
                "name": "Tourist",
                "visual_prompt": "A friendly tourist in casual clothes, smiling broadly"
            }
        ],
        # Audio settings (v0.4)
        "audio_enabled": False,
        "audio_file_path": "",
        "audio_volume": 0.8,
        "audio_fade_in": 1.0,
        "audio_fade_out": 2.0,
        "audio_loop": True,
        "audio_normalize": True,
        # Variants settings (v0.5)
        "variants_enabled": False,
        "selected_variants": [],
        # Template state (v0.5)
        "selected_template": None,
        "template_category_filter": "all",
        # Pipeline state
        "pipeline_status": "idle",  # idle, running, paused, complete, error
        "current_step": 0,
        "total_steps": 0,
        "logs": [],
        # Batch state (v0.5)
        "batch_status": "idle",
        "batch_summary": None,
        # Pipeline runner (v0.5)
        "pipeline_runner": None,
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Clear incompatible video_model strings from existing sessions
    # This handles users who have an old session with fal-ai/kling models
    if st.session_state.video_provider == "replicate" and st.session_state.video_model:
        if "fal-ai" in st.session_state.video_model or "kling" in st.session_state.video_model.lower():
            st.session_state.video_model = ""

init_session_state()

# Initialize template loader
@st.cache_resource
def get_template_loader():
    """Get cached template loader."""
    return TemplateLoader()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def generate_id() -> str:
    """Generate a short unique ID for subjects."""
    return f"subj_{uuid.uuid4().hex[:6]}"


def load_config_file(uploaded_file) -> Optional[dict]:
    """Parse uploaded JSON config file."""
    try:
        content = uploaded_file.read().decode("utf-8")
        return json.loads(content)
    except Exception as e:
        st.error(f"Failed to parse config: {e}")
        return None


def apply_config(config: dict):
    """Apply loaded config to session state."""
    if "project_name" in config:
        st.session_state.project_name = config["project_name"]
    if "output_folder" in config:
        st.session_state.output_folder = config["output_folder"]
    if "settings" in config:
        s = config["settings"]
        st.session_state.aspect_ratio = s.get("aspect_ratio", "9:16")
        st.session_state.transition_duration = s.get("transition_duration_sec", 5)
        st.session_state.image_model = s.get("image_model", st.session_state.image_model)
        st.session_state.video_provider = s.get("video_provider", st.session_state.video_provider)
        # Only use video_model from config if it matches the current provider
        # Ignore fal-ai/kling model strings when using replicate provider
        config_model = s.get("video_model", "")
        if st.session_state.video_provider == "replicate" and config_model:
            if "fal-ai" in config_model or "kling" in config_model.lower():
                config_model = ""  # Clear incompatible model
        st.session_state.video_model = config_model if config_model else st.session_state.video_model
    if "global_scene" in config:
        g = config["global_scene"]
        st.session_state.location_prompt = g.get("location_prompt", "")
        st.session_state.negative_prompt = g.get("negative_prompt", "")
    if "sequence" in config:
        st.session_state.sequence = config["sequence"]
    # Apply audio settings (v0.4)
    if "audio" in config:
        a = config["audio"]
        st.session_state.audio_enabled = a.get("enabled", False)
        st.session_state.audio_file_path = a.get("audio_path", "")
        st.session_state.audio_volume = a.get("volume", 0.8)
        st.session_state.audio_fade_in = a.get("fade_in_sec", 1.0)
        st.session_state.audio_fade_out = a.get("fade_out_sec", 2.0)
        st.session_state.audio_loop = a.get("loop", True)
        st.session_state.audio_normalize = a.get("normalize", True)


def export_config() -> dict:
    """Generate config dict from current session state."""
    config = {
        "project_name": st.session_state.project_name,
        "output_folder": st.session_state.output_folder,
        "settings": {
            "aspect_ratio": st.session_state.aspect_ratio,
            "transition_duration_sec": st.session_state.transition_duration,
            "image_model": st.session_state.image_model,
            "video_provider": st.session_state.video_provider,
            "video_model": st.session_state.video_model,
            "variants": st.session_state.selected_variants if st.session_state.variants_enabled else []
        },
        "global_scene": {
            "location_prompt": st.session_state.location_prompt,
            "negative_prompt": st.session_state.negative_prompt
        },
        "audio": {
            "enabled": st.session_state.audio_enabled,
            "audio_path": st.session_state.audio_file_path,
            "volume": st.session_state.audio_volume,
            "fade_in_sec": st.session_state.audio_fade_in,
            "fade_out_sec": st.session_state.audio_fade_out,
            "loop": st.session_state.audio_loop,
            "normalize": st.session_state.audio_normalize
        },
        "sequence": st.session_state.sequence
    }
    return config


def apply_template_to_state(template: Template):
    """Apply a template to the current session state."""
    config = template.base_config

    if "project_name" in config:
        st.session_state.project_name = config["project_name"]
    if "output_folder" in config:
        st.session_state.output_folder = config["output_folder"]
    if "settings" in config:
        s = config["settings"]
        st.session_state.aspect_ratio = s.get("aspect_ratio", "9:16")
        st.session_state.transition_duration = s.get("transition_duration_sec", 5)
        st.session_state.image_model = s.get("image_model", st.session_state.image_model)
        st.session_state.video_provider = s.get("video_provider", st.session_state.video_provider)
        # Only use video_model from template if it matches the current provider
        # Ignore fal-ai/kling model strings when using replicate provider
        template_model = s.get("video_model", "")
        if st.session_state.video_provider == "replicate" and template_model:
            # Check if model is incompatible with Replicate (e.g., fal-ai, kling)
            if "fal-ai" in template_model or "kling" in template_model.lower():
                template_model = ""  # Clear incompatible model
        st.session_state.video_model = template_model if template_model else st.session_state.video_model
        if "variants" in s:
            st.session_state.selected_variants = s["variants"]
            st.session_state.variants_enabled = len(s["variants"]) > 0
    if "global_scene" in config:
        g = config["global_scene"]
        st.session_state.location_prompt = g.get("location_prompt", "")
        st.session_state.negative_prompt = g.get("negative_prompt", "")
    if "sequence" in config:
        st.session_state.sequence = config["sequence"]
    if "audio" in config:
        a = config["audio"]
        st.session_state.audio_enabled = a.get("enabled", False)
        st.session_state.audio_file_path = a.get("audio_path", "")
        st.session_state.audio_volume = a.get("volume", 0.8)
        st.session_state.audio_fade_in = a.get("fade_in_sec", 1.0)
        st.session_state.audio_fade_out = a.get("fade_out_sec", 2.0)
        st.session_state.audio_loop = a.get("loop", True)
        st.session_state.audio_normalize = a.get("normalize", True)
    
    st.session_state.selected_template = template.name


def add_subject(name: str = "", visual_prompt: str = ""):
    """Add a new subject to the sequence."""
    new_subject = {
        "id": generate_id(),
        "name": name or f"Subject {len(st.session_state.sequence) + 1}",
        "visual_prompt": visual_prompt or "Describe the person's appearance"
    }
    st.session_state.sequence.append(new_subject)


def remove_subject(index: int):
    """Remove subject at given index (anchor at 0 cannot be removed)."""
    if index > 0 and index < len(st.session_state.sequence):
        st.session_state.sequence.pop(index)


def move_subject(index: int, direction: int):
    """Move subject up (-1) or down (+1) in sequence."""
    # Anchor (index 0) cannot be moved
    if index == 0:
        return
    new_index = index + direction
    if 1 <= new_index < len(st.session_state.sequence):
        seq = st.session_state.sequence
        seq[index], seq[new_index] = seq[new_index], seq[index]


def calculate_estimates() -> dict:
    """Calculate time and cost estimates for current config."""
    num_subjects = len(st.session_state.sequence)
    num_morphs = max(0, num_subjects - 1)
    
    # Rough estimates based on typical API times
    image_time_sec = 15  # per image
    video_time_sec = 120  # per morph video
    variant_time_sec = 10  # per variant
    
    total_images = num_subjects
    total_videos = num_morphs
    total_variants = len(st.session_state.selected_variants) if st.session_state.variants_enabled else 0
    
    estimated_time_sec = (
        (total_images * image_time_sec) + 
        (total_videos * video_time_sec) +
        (total_variants * variant_time_sec)
    )
    
    # Cost estimates (approximate)
    image_cost = 0.05  # per image
    video_cost = 0.50  # per video
    
    estimated_cost = (total_images * image_cost) + (total_videos * video_cost)
    
    final_duration = num_morphs * st.session_state.transition_duration
    
    return {
        "images": total_images,
        "videos": total_videos,
        "variants": total_variants,
        "time_minutes": round(estimated_time_sec / 60, 1),
        "cost_usd": round(estimated_cost, 2),
        "final_duration_sec": final_duration
    }


# =============================================================================
# SIDEBAR - Settings & Configuration
# =============================================================================

with st.sidebar:
    # Logo and title
    st.markdown("""
    <div style="margin-bottom: 2rem;">
        <span style="font-size: 2rem;">🌟</span>
        <span style="font-size: 1.25rem; font-weight: 600; margin-left: 0.5rem; color: var(--snow);">StarStitch</span>
        <p style="color: var(--silver); font-size: 0.8125rem; margin-top: 0.25rem;">v0.5 Batch Processing & Templates</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Project settings
    st.markdown("#### Project")
    st.session_state.project_name = st.text_input(
        "Project Name",
        value=st.session_state.project_name,
        help="Used for output folder naming"
    )
    
    st.session_state.output_folder = st.text_input(
        "Output Folder",
        value=st.session_state.output_folder
    )
    
    st.markdown("---")
    
    # Generation settings
    st.markdown("#### Generation Settings")
    
    st.session_state.aspect_ratio = st.selectbox(
        "Aspect Ratio",
        options=["9:16", "16:9", "1:1", "4:3", "3:4"],
        index=["9:16", "16:9", "1:1", "4:3", "3:4"].index(st.session_state.aspect_ratio),
        help="9:16 for TikTok/Reels, 16:9 for YouTube"
    )
    
    st.session_state.transition_duration = st.slider(
        "Transition Duration (sec)",
        min_value=2,
        max_value=10,
        value=st.session_state.transition_duration,
        help="Duration of each morph transition"
    )
    
    st.markdown("---")
    
    # Model selection
    st.markdown("#### AI Models")
    
    image_models = [
        "black-forest-labs/flux-1.1-pro",
        "black-forest-labs/flux-schnell",
        "stability-ai/sdxl"
    ]
    st.session_state.image_model = st.selectbox(
        "Image Model",
        options=image_models,
        index=image_models.index(st.session_state.image_model) if st.session_state.image_model in image_models else 0,
        help="Model used for generating subject images"
    )
    
    # Video provider selection - Replicate/Veo is fastest and uses existing API key
    video_providers = ["replicate", "fal", "runway", "luma"]
    provider_labels = {
        "replicate": "Veo 3.1 Fast via Replicate (~1 min, $0.10/sec)",
        "fal": "Fal.ai / Kling (Slow 10+ min, $0.07/sec)",
        "runway": "Runway Gen-3 (requires separate API key)",
        "luma": "Luma Dream Machine"
    }
    current_provider = st.session_state.video_provider
    if current_provider not in video_providers:
        current_provider = "replicate"

    st.session_state.video_provider = st.selectbox(
        "Video Provider",
        options=video_providers,
        index=video_providers.index(current_provider),
        format_func=lambda x: provider_labels.get(x, x),
        help="Veo 3.1 Fast is recommended - uses your existing Replicate key, ~1 min per video"
    )
    
    st.markdown("---")
    
    # Config import/export
    st.markdown("#### Configuration")
    
    uploaded_config = st.file_uploader(
        "Import config.json",
        type=["json"],
        help="Load a previously saved configuration"
    )
    
    if uploaded_config:
        config = load_config_file(uploaded_config)
        if config:
            apply_config(config)
            st.success("Config loaded!")
            st.rerun()
    
    # Export button
    config_json = json.dumps(export_config(), indent=2)
    st.download_button(
        label="Export Config",
        data=config_json,
        file_name=f"{st.session_state.project_name}_config.json",
        mime="application/json"
    )


# =============================================================================
# MAIN CONTENT
# =============================================================================

# Header
st.markdown("""
<div class="header-container">
    <span class="header-logo">🌟</span>
    <div>
        <h1 class="header-title">StarStitch</h1>
        <p class="header-subtitle">AI-Powered Video Morphing Pipeline</p>
    </div>
</div>
""", unsafe_allow_html=True)

# About section
with st.expander("What is StarStitch?", expanded=False):
    st.markdown("""
**StarStitch creates seamless "morphing selfie" video chains.** Give it a list of people and a location,
and it generates a continuous video where one person appears to morph into the next while maintaining
the same selfie angle.

**How it works:**
1. **Add subjects** — Define your sequence of people (celebrities, team members, anyone)
2. **Set the scene** — Choose a location and visual style for the selfie
3. **Generate** — AI creates images for each person, then morphs between them
4. **The magic** — The last frame of each transition becomes the first frame of the next, creating pixel-perfect continuity

**Workflow:**
- **Templates** — Start with a pre-built template or create from scratch
- **Sequence** — Add and reorder subjects in your morph chain
- **Scene** — Configure location, lighting, and quality settings
- **Audio** — Add background music with volume and fade controls
- **Variants** — Generate multiple aspect ratios (9:16, 16:9, 1:1)
- **Generate** — Run the pipeline and export your video

**Requirements:** Replicate API key (images) + Fal.ai API key (video morphing)
    """)

st.markdown("---")

# Tabs for main sections
tab_templates, tab_sequence, tab_scene, tab_audio, tab_variants, tab_preview, tab_generate = st.tabs([
    "📁 Templates",
    "📋 Sequence",
    "🎬 Scene",
    "🎵 Audio",
    "📐 Variants",
    "👁️ Preview",
    "🚀 Generate"
])


# =============================================================================
# TAB: TEMPLATES
# =============================================================================

with tab_templates:
    st.markdown("### Template Browser")
    st.markdown("Browse pre-built scene templates to quickly start your project. Templates provide starting configurations that you can customize.")
    
    st.markdown("---")
    
    # Get template loader
    template_loader = get_template_loader()
    all_templates = template_loader.list_templates()
    
    if not all_templates:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📁</div>
            <p>No templates found</p>
            <p>Templates should be in the ./templates directory</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Category filter
        categories = ["all"] + list(set(t.category for t in all_templates))
        
        col_filter, col_search = st.columns([1, 2])
        
        with col_filter:
            selected_category = st.selectbox(
                "Category",
                options=categories,
                index=categories.index(st.session_state.template_category_filter) if st.session_state.template_category_filter in categories else 0,
                format_func=lambda x: x.capitalize() if x != "all" else "All Categories"
            )
            st.session_state.template_category_filter = selected_category
        
        with col_search:
            search_query = st.text_input(
                "Search templates",
                placeholder="Search by name, description, or tags..."
            )
        
        st.markdown("---")
        
        # Filter templates
        filtered_templates = all_templates
        if selected_category != "all":
            filtered_templates = [t for t in filtered_templates if t.category == selected_category]
        if search_query:
            filtered_templates = template_loader.search_templates(search_query)
            if selected_category != "all":
                filtered_templates = [t for t in filtered_templates if t.category == selected_category]
        
        # Current template indicator
        if st.session_state.selected_template:
            st.markdown(f"**Currently using:** `{st.session_state.selected_template}`")
            if st.button("Clear Template", key="clear_template"):
                st.session_state.selected_template = None
                st.rerun()
            st.markdown("---")
        
        # Template grid
        if filtered_templates:
            # Display templates in rows of 3
            for i in range(0, len(filtered_templates), 3):
                cols = st.columns(3)
                for j, col in enumerate(cols):
                    if i + j < len(filtered_templates):
                        template = filtered_templates[i + j]
                        with col:
                            is_selected = st.session_state.selected_template == template.name

                            with st.container(border=True):
                                # Category badge and selected indicator
                                badge_col, check_col = st.columns([4, 1])
                                with badge_col:
                                    st.caption(f"**{template.category.upper()}**")
                                with check_col:
                                    if is_selected:
                                        st.markdown("✓")

                                # Template name
                                st.markdown(f"**{template.display_name}**")

                                # Description
                                desc = template.description[:80] + ('...' if len(template.description) > 80 else '')
                                st.caption(desc)

                                # Tags
                                if template.tags:
                                    st.caption(" · ".join(template.tags[:3]))

                            if st.button(
                                "Use Template" if not is_selected else "Selected",
                                key=f"use_template_{template.name}",
                                disabled=is_selected,
                                use_container_width=True
                            ):
                                apply_template_to_state(template)
                                st.success(f"Applied template: {template.display_name}")
                                st.rerun()
        else:
            st.info("No templates match your search")
        
        st.markdown("---")
        
        # Template stats
        st.markdown("##### Template Library Stats")
        stats_cols = st.columns(4)
        
        category_counts = {}
        for t in all_templates:
            category_counts[t.category] = category_counts.get(t.category, 0) + 1
        
        for i, (cat, count) in enumerate(category_counts.items()):
            with stats_cols[i % 4]:
                st.metric(cat.capitalize(), count)


# =============================================================================
# TAB: SEQUENCE BUILDER
# =============================================================================

with tab_sequence:
    st.markdown("### Morph Sequence")
    st.markdown("Define the subjects that will morph into each other. The first subject is the **anchor** — the starting point of your chain.")
    
    # Sequence metrics
    estimates = calculate_estimates()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Subjects", len(st.session_state.sequence))
    with col2:
        st.metric("Transitions", estimates["videos"])
    with col3:
        st.metric("Est. Time", f"{estimates['time_minutes']}m")
    with col4:
        st.metric("Final Duration", f"{estimates['final_duration_sec']}s")
    
    st.markdown("---")
    
    # Subject cards
    for i, subject in enumerate(st.session_state.sequence):
        is_anchor = i == 0
        
        with st.container():
            cols = st.columns([0.05, 0.3, 0.5, 0.15])
            
            # Index indicator
            with cols[0]:
                if is_anchor:
                    st.markdown("🎯")
                else:
                    st.markdown(f"**{i}**")
            
            # Name field
            with cols[1]:
                new_name = st.text_input(
                    "Name" if is_anchor else f"Name###{i}",
                    value=subject["name"],
                    key=f"name_{subject['id']}",
                    label_visibility="collapsed" if not is_anchor else "visible",
                    placeholder="Subject name"
                )
                if new_name != subject["name"]:
                    st.session_state.sequence[i]["name"] = new_name
            
            # Visual prompt
            with cols[2]:
                new_prompt = st.text_input(
                    "Visual Prompt" if is_anchor else f"Visual Prompt###{i}",
                    value=subject["visual_prompt"],
                    key=f"prompt_{subject['id']}",
                    label_visibility="collapsed" if not is_anchor else "visible",
                    placeholder="Describe their appearance..."
                )
                if new_prompt != subject["visual_prompt"]:
                    st.session_state.sequence[i]["visual_prompt"] = new_prompt
            
            # Actions
            with cols[3]:
                if is_anchor:
                    st.markdown("##### Actions")
                else:
                    action_cols = st.columns(3)
                    with action_cols[0]:
                        if i > 1:  # Can't move up if already at position 1
                            if st.button("↑", key=f"up_{subject['id']}", help="Move up"):
                                move_subject(i, -1)
                                st.rerun()
                    with action_cols[1]:
                        if i < len(st.session_state.sequence) - 1:
                            if st.button("↓", key=f"down_{subject['id']}", help="Move down"):
                                move_subject(i, 1)
                                st.rerun()
                    with action_cols[2]:
                        if st.button("✕", key=f"del_{subject['id']}", help="Remove"):
                            remove_subject(i)
                            st.rerun()
        
        if i < len(st.session_state.sequence) - 1:
            st.markdown('<div style="text-align: center; color: var(--silver); margin: 0.5rem 0; font-size: 0.875rem;">↓ morphs into ↓</div>', unsafe_allow_html=True)
    
    # Add subject button
    st.markdown("---")
    col_add, col_spacer = st.columns([1, 3])
    with col_add:
        if st.button("+ Add Subject", use_container_width=True):
            add_subject()
            st.rerun()


# =============================================================================
# TAB: SCENE CONFIGURATION
# =============================================================================

with tab_scene:
    st.markdown("### Global Scene")
    st.markdown("These settings apply to all generated images, ensuring visual consistency across the morph chain.")
    
    st.markdown("---")
    
    st.markdown("##### Location & Setting")
    st.session_state.location_prompt = st.text_area(
        "Location Prompt",
        value=st.session_state.location_prompt,
        height=100,
        help="Describe the scene, lighting, and camera angle. This prompt is combined with each subject's visual prompt.",
        placeholder="e.g., taking a selfie at the Eiffel Tower, golden hour lighting, 4k photorealistic"
    )
    
    st.markdown("##### Quality Control")
    st.session_state.negative_prompt = st.text_area(
        "Negative Prompt",
        value=st.session_state.negative_prompt,
        height=80,
        help="Describe what to avoid in generated images.",
        placeholder="e.g., blurry, distorted, cartoon, low quality"
    )
    
    st.markdown("---")
    
    # Scene presets
    st.markdown("##### Quick Presets")
    preset_cols = st.columns(4)
    
    presets = {
        "Eiffel Tower": "taking a selfie at the Eiffel Tower, golden hour lighting, 4k photorealistic",
        "Times Square": "taking a selfie in Times Square New York, neon lights, nighttime, cinematic",
        "Beach Sunset": "taking a selfie on a tropical beach at sunset, warm colors, paradise vibes",
        "Studio": "professional headshot in a photo studio, neutral background, soft lighting"
    }
    
    for i, (name, prompt) in enumerate(presets.items()):
        with preset_cols[i]:
            if st.button(name, key=f"preset_{i}", use_container_width=True):
                st.session_state.location_prompt = prompt
                st.rerun()


# =============================================================================
# TAB: AUDIO SETTINGS (v0.4)
# =============================================================================

with tab_audio:
    st.markdown("### Background Audio")
    st.markdown("Add background music or ambient sound to your final video.")
    
    st.markdown("---")
    
    # Enable/disable audio
    col_toggle, col_spacer = st.columns([1, 2])
    with col_toggle:
        st.session_state.audio_enabled = st.toggle(
            "Enable Audio Track",
            value=st.session_state.audio_enabled,
            help="Add background audio to the final video"
        )
    
    if st.session_state.audio_enabled:
        st.markdown("---")
        
        # Audio file upload
        st.markdown("##### Audio File")
        
        uploaded_audio = st.file_uploader(
            "Upload Audio",
            type=["mp3", "wav", "m4a", "aac", "flac", "ogg"],
            help="Supported formats: MP3, WAV, M4A, AAC, FLAC, OGG"
        )
        
        if uploaded_audio:
            # Save uploaded file to temp location
            audio_dir = Path(st.session_state.output_folder) / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            audio_save_path = audio_dir / uploaded_audio.name
            
            with open(audio_save_path, "wb") as f:
                f.write(uploaded_audio.read())
            
            st.session_state.audio_file_path = str(audio_save_path)
            st.success(f"Audio file saved: {uploaded_audio.name}")
        
        # Show current audio file
        if st.session_state.audio_file_path:
            current_file = Path(st.session_state.audio_file_path)
            if current_file.exists():
                st.markdown(f"**Current file:** `{current_file.name}`")
            else:
                st.warning("Previously selected audio file not found.")
        
        # Or specify path manually
        manual_path = st.text_input(
            "Or enter audio file path",
            value=st.session_state.audio_file_path,
            placeholder="/path/to/your/audio.mp3",
            help="You can also specify a path to an existing audio file"
        )
        if manual_path != st.session_state.audio_file_path:
            st.session_state.audio_file_path = manual_path
        
        st.markdown("---")
        
        # Volume settings
        st.markdown("##### Volume & Mixing")
        
        col_vol, col_norm = st.columns(2)
        
        with col_vol:
            st.session_state.audio_volume = st.slider(
                "Volume",
                min_value=0.0,
                max_value=1.0,
                value=st.session_state.audio_volume,
                step=0.05,
                format="%.0f%%",
                help="Audio volume level (0% = silent, 100% = full volume)"
            )
            st.caption(f"Volume: {st.session_state.audio_volume * 100:.0f}%")
        
        with col_norm:
            st.session_state.audio_normalize = st.checkbox(
                "Normalize Audio",
                value=st.session_state.audio_normalize,
                help="Automatically adjust audio levels for consistent volume"
            )
        
        st.markdown("---")
        
        # Fade settings
        st.markdown("##### Fade Effects")
        
        col_fade_in, col_fade_out = st.columns(2)
        
        with col_fade_in:
            st.session_state.audio_fade_in = st.slider(
                "Fade In (seconds)",
                min_value=0.0,
                max_value=5.0,
                value=st.session_state.audio_fade_in,
                step=0.5,
                help="Gradually increase volume at the start"
            )
        
        with col_fade_out:
            st.session_state.audio_fade_out = st.slider(
                "Fade Out (seconds)",
                min_value=0.0,
                max_value=5.0,
                value=st.session_state.audio_fade_out,
                step=0.5,
                help="Gradually decrease volume at the end"
            )
        
        st.markdown("---")
        
        # Duration handling
        st.markdown("##### Duration Handling")
        
        st.session_state.audio_loop = st.checkbox(
            "Loop audio if shorter than video",
            value=st.session_state.audio_loop,
            help="If the audio is shorter than the video, it will seamlessly loop"
        )
        
        # Preview summary
        st.markdown("---")
        st.markdown("##### Audio Settings Summary")
        
        estimates = calculate_estimates()
        video_duration = estimates["final_duration_sec"]
        
        summary_items = [
            f"**File:** {Path(st.session_state.audio_file_path).name if st.session_state.audio_file_path else 'Not selected'}",
            f"**Volume:** {st.session_state.audio_volume * 100:.0f}%",
            f"**Fade In:** {st.session_state.audio_fade_in}s | **Fade Out:** {st.session_state.audio_fade_out}s",
            f"**Loop:** {'Enabled' if st.session_state.audio_loop else 'Disabled'}",
            f"**Normalize:** {'Yes' if st.session_state.audio_normalize else 'No'}",
            f"**Video Duration:** ~{video_duration}s"
        ]
        
        for item in summary_items:
            st.markdown(item)
    
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">🔇</div>
            <p>Audio is disabled</p>
            <p>Enable the toggle above to add background music</p>
        </div>
        """, unsafe_allow_html=True)


# =============================================================================
# TAB: VARIANTS
# =============================================================================

with tab_variants:
    st.markdown("### Output Variants")
    st.markdown("Generate multiple aspect ratio versions of your final video from a single render. Perfect for multi-platform distribution.")
    
    st.markdown("---")
    
    # Enable/disable variants
    col_toggle, col_spacer = st.columns([1, 2])
    with col_toggle:
        st.session_state.variants_enabled = st.toggle(
            "Enable Variants",
            value=st.session_state.variants_enabled,
            help="Generate additional aspect ratio versions"
        )
    
    if st.session_state.variants_enabled:
        st.markdown("---")
        
        st.markdown("##### Select Output Formats")
        st.markdown("Choose which aspect ratios to generate. Your primary ratio is automatically included.")
        
        # Available variants with descriptions
        variant_options = {
            "9:16": {"name": "TikTok / Reels", "desc": "Vertical (1080x1920)", "icon": "📱"},
            "16:9": {"name": "YouTube / Landscape", "desc": "Horizontal (1920x1080)", "icon": "🖥️"},
            "1:1": {"name": "Instagram / Square", "desc": "Square (1080x1080)", "icon": "⬜"},
            "4:5": {"name": "Instagram / Portrait", "desc": "Portrait (1080x1350)", "icon": "📷"},
            "4:3": {"name": "Standard", "desc": "Classic (1440x1080)", "icon": "📺"},
        }
        
        # Current primary ratio
        primary_ratio = st.session_state.aspect_ratio
        st.markdown(f"**Primary ratio:** {primary_ratio} (from settings)")
        
        st.markdown("---")
        
        # Variant checkboxes
        selected = []
        
        cols = st.columns(3)
        
        for i, (ratio, info) in enumerate(variant_options.items()):
            col = cols[i % 3]
            with col:
                is_primary = ratio == primary_ratio
                
                if is_primary:
                    st.markdown(f"""
                    <div style="
                        background: rgba(34, 197, 94, 0.15);
                        border: 1px solid rgba(34, 197, 94, 0.4);
                        border-radius: 10px;
                        padding: 1rem;
                        margin-bottom: 0.5rem;
                    ">
                        <span style="font-size: 1.25rem;">{info['icon']}</span>
                        <span style="font-weight: 600; color: var(--neon-emerald); margin-left: 0.5rem;">{ratio}</span>
                        <span style="color: var(--cloud); font-size: 0.875rem; display: block; margin-top: 0.25rem;">{info['name']}</span>
                        <span style="color: var(--neon-emerald); font-size: 0.75rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;">PRIMARY</span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    checked = ratio in st.session_state.selected_variants
                    if st.checkbox(
                        f"{info['icon']} {ratio} - {info['name']}",
                        value=checked,
                        key=f"variant_{ratio}"
                    ):
                        selected.append(ratio)
        
        st.session_state.selected_variants = selected
        
        st.markdown("---")
        
        # Summary
        st.markdown("##### Variant Summary")
        
        total_variants = len(selected)
        variant_list = [primary_ratio] + selected
        
        st.markdown(f"**Total outputs:** {total_variants + 1} videos")
        st.markdown(f"**Formats:** {', '.join(variant_list)}")
        
        if total_variants > 0:
            st.markdown("""
            <div class="info-box" style="margin-top: 1rem;">
                <span style="color: var(--aurora-mid);">ℹ️</span>
                <span style="color: var(--cloud); font-size: 0.9375rem; margin-left: 0.5rem;">
                    Variants are created by cropping and scaling the final video.
                    Center framing works best for multi-ratio output.
                </span>
            </div>
            """, unsafe_allow_html=True)
    
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📐</div>
            <p>Variants are disabled</p>
            <p>Enable to generate multiple aspect ratio versions</p>
        </div>
        """, unsafe_allow_html=True)


# =============================================================================
# TAB: PREVIEW
# =============================================================================

with tab_preview:
    st.markdown("### Configuration Preview")
    st.markdown("Review your complete configuration before generating.")
    
    st.markdown("---")
    
    # Visual sequence preview
    st.markdown("##### Morph Sequence")
    
    if len(st.session_state.sequence) > 0:
        # Create visual flow
        seq_cols = st.columns(min(len(st.session_state.sequence), 5))
        for i, (col, subject) in enumerate(zip(seq_cols, st.session_state.sequence[:5])):
            with col:
                border_color = 'var(--aurora-mid)' if i == 0 else 'var(--border-subtle)'
                st.markdown(f"""
                <div style="
                    background: var(--ash);
                    border: 1px solid {border_color};
                    border-radius: 10px;
                    padding: 1rem;
                    text-align: center;
                ">
                    <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">
                        {'🎯' if i == 0 else '👤'}
                    </div>
                    <div style="font-weight: 500; color: var(--snow); font-size: 0.9375rem;">
                        {subject['name']}
                    </div>
                    <div style="color: var(--silver); font-size: 0.8125rem; margin-top: 0.25rem;">
                        {'Anchor' if i == 0 else f'#{i}'}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            if i < len(st.session_state.sequence) - 1 and i < 4:
                pass  # Arrow would go here in between
        
        if len(st.session_state.sequence) > 5:
            st.markdown(f"*... and {len(st.session_state.sequence) - 5} more subjects*")
    
    st.markdown("---")
    
    # Summary stats
    st.markdown("##### Estimates")
    
    estimates_preview = calculate_estimates()
    
    est_cols = st.columns(5)
    with est_cols[0]:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{estimates_preview['images']}</div>
            <div class="metric-label">Images</div>
        </div>
        """, unsafe_allow_html=True)
    with est_cols[1]:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{estimates_preview['videos']}</div>
            <div class="metric-label">Videos</div>
        </div>
        """, unsafe_allow_html=True)
    with est_cols[2]:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{estimates_preview['variants']}</div>
            <div class="metric-label">Variants</div>
        </div>
        """, unsafe_allow_html=True)
    with est_cols[3]:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">~{estimates_preview['time_minutes']}m</div>
            <div class="metric-label">Gen Time</div>
        </div>
        """, unsafe_allow_html=True)
    with est_cols[4]:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">${estimates_preview['cost_usd']}</div>
            <div class="metric-label">Est. Cost</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # JSON preview
    st.markdown("##### JSON Configuration")
    
    with st.expander("View raw config.json", expanded=False):
        st.code(json.dumps(export_config(), indent=2), language="json")


# =============================================================================
# TAB: GENERATE
# =============================================================================

with tab_generate:
    st.markdown("### Generate Video")
    st.markdown("Start the StarStitch pipeline to generate your morphing video chain.")
    
    st.markdown("---")
    
    # Pre-flight checks
    st.markdown("##### Pre-flight Checks")
    
    checks = []
    
    # Check sequence length
    if len(st.session_state.sequence) < 2:
        checks.append(("❌", "Add at least 2 subjects to create a morph", False))
    else:
        checks.append(("✓", f"{len(st.session_state.sequence)} subjects configured", True))
    
    # Check location prompt
    if not st.session_state.location_prompt.strip():
        checks.append(("❌", "Location prompt is empty", False))
    else:
        checks.append(("✓", "Location prompt set", True))
    
    # Check for empty visual prompts
    empty_prompts = [s for s in st.session_state.sequence if not s["visual_prompt"].strip()]
    if empty_prompts:
        checks.append(("⚠️", f"{len(empty_prompts)} subjects missing visual prompts", False))
    else:
        checks.append(("✓", "All visual prompts defined", True))
    
    # Check API keys (environment)
    replicate_key = os.environ.get("REPLICATE_API_TOKEN", "")

    if not replicate_key:
        checks.append(("⚠️", "REPLICATE_API_TOKEN not set in environment", False))
    else:
        checks.append(("✓", "Replicate API configured", True))

    # Check video provider API key based on selected provider
    video_provider = st.session_state.video_provider
    if video_provider == "replicate":
        # Replicate uses same key as image generation - already validated above
        if replicate_key:
            checks.append(("✓", "Video: Veo 3.1 Fast via Replicate (~1 min/video)", True))
        # If not set, the Replicate check above already flagged it
    elif video_provider == "runway":
        runway_key = os.environ.get("RUNWAY_API_KEY", "")
        if not runway_key:
            checks.append(("⚠️", "RUNWAY_API_KEY not set in environment", False))
        else:
            checks.append(("✓", "Runway API configured", True))
    elif video_provider == "fal":
        fal_key = os.environ.get("FAL_KEY", "")
        if not fal_key:
            checks.append(("⚠️", "FAL_KEY not set in environment", False))
        else:
            checks.append(("✓", "Fal.ai/Kling API configured (slow 10+ min/video)", True))
    elif video_provider == "luma":
        luma_key = os.environ.get("LUMAAI_API_KEY", "")
        if not luma_key:
            checks.append(("⚠️", "LUMAAI_API_KEY not set in environment", False))
        else:
            checks.append(("✓", "Luma AI API configured", True))
    
    # Check audio configuration (v0.4)
    if st.session_state.audio_enabled:
        if not st.session_state.audio_file_path:
            checks.append(("⚠️", "Audio enabled but no file selected", False))
        elif not Path(st.session_state.audio_file_path).exists():
            checks.append(("⚠️", f"Audio file not found: {st.session_state.audio_file_path}", False))
        else:
            checks.append(("✓", f"Audio: {Path(st.session_state.audio_file_path).name}", True))
    else:
        checks.append(("ℹ️", "Audio track disabled (optional)", True))
    
    # Check variants (v0.5)
    if st.session_state.variants_enabled:
        num_variants = len(st.session_state.selected_variants)
        if num_variants > 0:
            checks.append(("✓", f"Variants: {num_variants} additional format(s)", True))
        else:
            checks.append(("ℹ️", "Variants enabled but none selected", True))
    else:
        checks.append(("ℹ️", "Output variants disabled (optional)", True))
    
    # Template info (v0.5)
    if st.session_state.selected_template:
        checks.append(("ℹ️", f"Using template: {st.session_state.selected_template}", True))
    
    # Display checks
    for icon, message, passed in checks:
        color = "#22c55e" if passed else ("#f59e0b" if icon == "⚠️" else "#ef4444")
        st.markdown(f'<span style="color: {color}; margin-right: 0.5rem;">{icon}</span> {message}', unsafe_allow_html=True)
    
    all_passed = all(c[2] for c in checks if c[0] != "⚠️")

    st.markdown("---")

    # =========================================================================
    # PIPELINE RUNNER INITIALIZATION
    # =========================================================================

    # Initialize runner if needed
    if st.session_state.pipeline_runner is None:
        st.session_state.pipeline_runner = PipelineRunner()

    runner = st.session_state.pipeline_runner
    progress = runner.get_progress()
    is_running = runner.is_running()

    # =========================================================================
    # GENERATION CONTROLS
    # =========================================================================

    col_gen, col_cancel = st.columns([3, 1])

    with col_gen:
        # Determine button state
        generate_disabled = not all_passed or is_running

        button_label = "🚀 Start Generation"
        if is_running:
            button_label = "⏳ Generating..."
        elif progress.status == PipelineStatus.COMPLETE:
            button_label = "🔄 Generate Again"

        if st.button(
            button_label,
            disabled=generate_disabled,
            use_container_width=True,
            type="primary"
        ):
            # Reset if previous run completed
            if progress.status in [PipelineStatus.COMPLETE, PipelineStatus.ERROR, PipelineStatus.CANCELLED]:
                runner.reset()

            # Get config and start pipeline
            config = export_config()
            runner.start(config)
            st.rerun()

    with col_cancel:
        if is_running:
            if st.button("Cancel", use_container_width=True, type="secondary"):
                runner.cancel()
                st.rerun()

    if generate_disabled and not is_running:
        st.caption("Fix the issues above to enable generation")

    # =========================================================================
    # PROGRESS DISPLAY
    # =========================================================================

    st.markdown("---")

    if is_running:
        # Show active progress
        st.markdown("##### Pipeline Running")

        # Progress bar
        if progress.total_steps > 0:
            pct = progress.current_step / progress.total_steps
            st.progress(pct, text=f"Step {progress.current_step}/{progress.total_steps}")
        else:
            st.progress(0.0, text="Initializing...")

        # Current phase/action
        if progress.current_phase:
            st.markdown(f"**{progress.current_phase}**")
        if progress.current_action:
            st.info(progress.current_action)

        # Elapsed time
        if progress.started_at:
            elapsed = (datetime.now() - progress.started_at).total_seconds()
            st.caption(f"Elapsed: {int(elapsed // 60)}m {int(elapsed % 60)}s")

        # Auto-refresh every 2 seconds
        time.sleep(2)
        st.rerun()

    elif progress.status == PipelineStatus.COMPLETE:
        # =====================================================================
        # SUCCESS: DISPLAY RESULTS
        # =====================================================================
        st.markdown("##### Generation Complete!")

        # Completion time
        if progress.started_at and progress.completed_at:
            duration = (progress.completed_at - progress.started_at).total_seconds()
            st.success(f"Completed in {int(duration // 60)}m {int(duration % 60)}s")

        st.markdown("---")

        # Main video display
        if progress.final_video_path and progress.final_video_path.exists():
            st.markdown("##### Final Video")

            # Constrain video to ~40% width using columns
            col_video, col_spacer = st.columns([2, 3])
            with col_video:
                st.video(str(progress.final_video_path))

            # File info
            file_size = progress.final_video_path.stat().st_size / (1024 * 1024)
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.caption(f"**Size:** {file_size:.1f} MB")
            with col_info2:
                st.caption(f"**Path:** `{progress.final_video_path}`")

            # Download button
            with open(progress.final_video_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download Video",
                    data=f.read(),
                    file_name=progress.final_video_path.name,
                    mime="video/mp4",
                    use_container_width=True
                )

        # Variant videos
        if progress.variant_paths:
            st.markdown("---")
            st.markdown("##### Format Variants")

            # Display variants in a grid
            num_variants = len(progress.variant_paths)
            variant_cols = st.columns(min(num_variants, 3))

            for i, (ratio, path) in enumerate(progress.variant_paths.items()):
                with variant_cols[i % 3]:
                    if path.exists():
                        st.markdown(f"**{ratio}**")
                        st.video(str(path))

                        file_size = path.stat().st_size / (1024 * 1024)
                        st.caption(f"{file_size:.1f} MB")

                        with open(path, "rb") as f:
                            st.download_button(
                                label=f"⬇️ {ratio}",
                                data=f.read(),
                                file_name=path.name,
                                mime="video/mp4",
                                key=f"download_{ratio.replace(':', '_')}",
                                use_container_width=True
                            )

        # Render directory link
        if progress.render_dir and progress.render_dir.exists():
            st.markdown("---")
            st.caption(f"All assets saved to: `{progress.render_dir}`")

    elif progress.status == PipelineStatus.ERROR:
        # =====================================================================
        # ERROR STATE
        # =====================================================================
        st.markdown("##### Generation Failed")
        st.error(f"Error: {progress.error_message}")

        st.markdown("**Troubleshooting:**")
        st.markdown("""
        - Check your API keys are valid
        - Verify network connectivity
        - Check the logs below for details
        """)

        if st.button("🔄 Try Again"):
            runner.reset()
            st.rerun()

    elif progress.status == PipelineStatus.CANCELLED:
        st.warning("Generation was cancelled.")
        if st.button("🔄 Start Fresh"):
            runner.reset()
            st.rerun()

    else:
        # IDLE state - show ready message
        st.markdown("##### Pipeline Status")
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">🎬</div>
            <p>Ready to generate</p>
            <p>Configure your sequence and click Start Generation</p>
        </div>
        """, unsafe_allow_html=True)

    # =========================================================================
    # LOGS SECTION (always visible when not idle)
    # =========================================================================
    if progress.status != PipelineStatus.IDLE:
        st.markdown("---")
        st.markdown("##### Pipeline Logs")

        with st.expander("View Logs", expanded=is_running):
            if progress.logs:
                # Display logs in reverse order (newest first)
                log_text = "\n".join(reversed(progress.logs[-50:]))
                st.code(log_text, language=None)
            else:
                st.text("No logs yet...")


# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: var(--silver); font-size: 0.8125rem; padding: 1.5rem 0;">
    StarStitch v0.5 — Batch Processing & Templates — Built with Streamlit
</div>
""", unsafe_allow_html=True)
