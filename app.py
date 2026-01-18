"""
StarStitch Web UI
A modern Streamlit interface for the AI video morphing pipeline.

Run with: streamlit run app.py
"""

import os
import sys
import json
import logging
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import asdict

import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import StarStitch components
from config import ConfigLoader, StarStitchConfig, SettingsConfig, ConfigError
from providers import (
    ImageGenerator,
    create_video_generator,
    VideoProviderFactory,
)
from providers.base_provider import ImageGenerationError, VideoGenerationError
from utils import FileManager, FFmpegUtils
from utils.ffmpeg_utils import FFmpegError

# Page configuration
st.set_page_config(
    page_title="StarStitch",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for dark theme
st.markdown("""
<style>
    /* Main app styling */
    .stApp {
        background: linear-gradient(180deg, #0a0a0f 0%, #141420 100%);
    }
    
    /* Card-like containers */
    .stExpander {
        background-color: rgba(30, 30, 45, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #ffffff !important;
    }
    
    /* Provider cards */
    .provider-card {
        background: linear-gradient(135deg, rgba(40, 40, 60, 0.8), rgba(30, 30, 45, 0.8));
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
    }
    
    .provider-card:hover {
        border-color: rgba(100, 200, 255, 0.4);
        box-shadow: 0 4px 20px rgba(100, 200, 255, 0.1);
    }
    
    .provider-card.selected {
        border-color: #4CAF50;
        box-shadow: 0 4px 20px rgba(76, 175, 80, 0.2);
    }
    
    /* Status indicators */
    .status-ready {
        color: #4CAF50;
    }
    
    .status-missing {
        color: #ff6b6b;
    }
    
    /* Progress styling */
    .stProgress > div > div {
        background: linear-gradient(90deg, #4CAF50, #8BC34A);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d0d15 0%, #1a1a2e 100%);
    }
    
    /* Metric cards */
    [data-testid="metric-container"] {
        background-color: rgba(30, 30, 45, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    defaults = {
        "config": None,
        "running": False,
        "current_step": "",
        "progress": 0.0,
        "logs": [],
        "error": None,
        "output_video": None,
        "subjects": [
            {"id": "anchor", "name": "Person 1", "visual_prompt": "A friendly person smiling"},
            {"id": "target_01", "name": "Person 2", "visual_prompt": "A different person with confident expression"},
        ],
        "video_provider": "fal",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_provider_status() -> Dict[str, Dict[str, Any]]:
    """Check which providers have API keys configured."""
    providers = VideoProviderFactory.get_all_provider_info()
    status = {}
    
    for provider in providers:
        provider_id = provider["id"]
        env_key = provider.get("env_key", "")
        has_key = bool(os.environ.get(env_key, ""))
        
        status[provider_id] = {
            **provider,
            "configured": has_key,
            "status": "ready" if has_key else "missing",
        }
    
    return status


def render_header():
    """Render the application header."""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("""
        # ✨ StarStitch
        ### AI-Powered Video Morphing Pipeline
        """)
    
    with col2:
        st.markdown("""
        <div style='text-align: right; padding-top: 1rem;'>
            <span style='color: #888;'>v0.3</span>
        </div>
        """, unsafe_allow_html=True)


def render_provider_selector():
    """Render the video provider selection UI."""
    st.markdown("### 🎬 Video Provider")
    
    provider_status = get_provider_status()
    
    # Create columns for provider cards
    cols = st.columns(3)
    
    provider_options = [
        ("fal", "Fal.ai (Kling)", "High-quality morphing via Kling v1.6 Pro", "🎯"),
        ("runway", "Runway ML", "Gen-3 Alpha Turbo for cinematic video", "🎬"),
        ("luma", "Luma AI", "Dream Machine for smooth transitions", "🌙"),
    ]
    
    for i, (provider_id, name, desc, icon) in enumerate(provider_options):
        with cols[i]:
            status = provider_status.get(provider_id, {})
            is_configured = status.get("configured", False)
            is_selected = st.session_state.video_provider == provider_id
            
            # Status indicator
            status_icon = "✅" if is_configured else "⚠️"
            status_text = "Ready" if is_configured else "API Key Missing"
            status_class = "status-ready" if is_configured else "status-missing"
            
            # Card styling
            border_color = "#4CAF50" if is_selected else "rgba(255,255,255,0.1)"
            bg_opacity = "0.9" if is_selected else "0.6"
            
            st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, rgba(40, 40, 60, {bg_opacity}), rgba(30, 30, 45, {bg_opacity}));
                border: 2px solid {border_color};
                border-radius: 12px;
                padding: 1rem;
                text-align: center;
                min-height: 160px;
            '>
                <div style='font-size: 2rem;'>{icon}</div>
                <div style='font-weight: 600; margin: 0.5rem 0;'>{name}</div>
                <div style='font-size: 0.8rem; color: #888; margin-bottom: 0.5rem;'>{desc}</div>
                <div class='{status_class}' style='font-size: 0.8rem;'>{status_icon} {status_text}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(
                "Select" if not is_selected else "Selected ✓",
                key=f"select_{provider_id}",
                disabled=is_selected,
                use_container_width=True,
            ):
                st.session_state.video_provider = provider_id
                st.rerun()


def render_settings_panel():
    """Render the settings configuration panel."""
    with st.expander("⚙️ Pipeline Settings", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            aspect_ratio = st.selectbox(
                "Aspect Ratio",
                options=["9:16", "16:9", "1:1"],
                index=0,
                help="Output video aspect ratio",
            )
        
        with col2:
            duration = st.selectbox(
                "Transition Duration",
                options=["5", "10"],
                index=0,
                help="Duration of each morph transition in seconds",
            )
        
        with col3:
            st.text_input(
                "Project Name",
                value="my_stitch",
                key="project_name",
                help="Name for this render project",
            )
    
    return {
        "aspect_ratio": aspect_ratio,
        "transition_duration": duration,
        "project_name": st.session_state.get("project_name", "my_stitch"),
    }


def render_scene_settings():
    """Render the global scene configuration."""
    with st.expander("🌍 Scene Settings", expanded=True):
        location_prompt = st.text_area(
            "Location/Scene Prompt",
            value="taking a selfie in Times Square at night, neon lights, 4k photorealistic",
            height=80,
            help="This will be appended to all subject prompts",
        )
        
        negative_prompt = st.text_input(
            "Negative Prompt",
            value="blurry, distorted, cartoon, low quality, extra limbs",
            help="Things to avoid in generated images",
        )
    
    return {
        "location_prompt": location_prompt,
        "negative_prompt": negative_prompt,
    }


def render_sequence_editor():
    """Render the subject sequence editor."""
    st.markdown("### 👥 Sequence")
    
    # Add subject button
    if st.button("➕ Add Subject", use_container_width=False):
        new_id = f"target_{len(st.session_state.subjects):02d}"
        st.session_state.subjects.append({
            "id": new_id,
            "name": f"Person {len(st.session_state.subjects) + 1}",
            "visual_prompt": "A person with unique appearance",
        })
        st.rerun()
    
    st.markdown("---")
    
    # Render each subject
    subjects_to_remove = []
    
    for i, subject in enumerate(st.session_state.subjects):
        col1, col2, col3 = st.columns([1, 3, 0.5])
        
        with col1:
            label = "🎯 Anchor" if i == 0 else f"Target {i}"
            st.markdown(f"**{label}**")
            subject["name"] = st.text_input(
                "Name",
                value=subject["name"],
                key=f"name_{i}",
                label_visibility="collapsed",
            )
        
        with col2:
            subject["visual_prompt"] = st.text_area(
                "Visual Prompt",
                value=subject["visual_prompt"],
                key=f"prompt_{i}",
                height=68,
                label_visibility="collapsed",
            )
        
        with col3:
            if i > 0:  # Can't remove anchor
                if st.button("🗑️", key=f"remove_{i}", help="Remove this subject"):
                    subjects_to_remove.append(i)
    
    # Remove subjects marked for deletion
    for i in reversed(subjects_to_remove):
        st.session_state.subjects.pop(i)
        st.rerun()


def build_config_dict(settings: Dict, scene: Dict) -> Dict[str, Any]:
    """Build a configuration dictionary from UI state."""
    return {
        "project_name": settings["project_name"],
        "output_folder": "renders",
        "settings": {
            "aspect_ratio": settings["aspect_ratio"],
            "transition_duration": settings["transition_duration"],
            "video_provider": st.session_state.video_provider,
            "image_model": "black-forest-labs/flux-1.1-pro",
            "video_model": get_default_model_for_provider(st.session_state.video_provider),
        },
        "global_scene": {
            "location_prompt": scene["location_prompt"],
            "negative_prompt": scene["negative_prompt"],
        },
        "sequence": st.session_state.subjects,
    }


def get_default_model_for_provider(provider_id: str) -> str:
    """Get the default model for a provider."""
    models = {
        "fal": "fal-ai/kling-video/v1.6/pro/image-to-video",
        "runway": "gen3a_turbo",
        "luma": "luma-dream-machine",
    }
    return models.get(provider_id, "")


def validate_configuration(config_dict: Dict) -> Optional[str]:
    """Validate configuration and return error message if invalid."""
    try:
        config = StarStitchConfig.from_dict(config_dict)
        config.validate()
        
        # Check if the selected provider has an API key
        provider_id = config_dict["settings"]["video_provider"]
        provider_info = VideoProviderFactory.get_provider_info(provider_id)
        env_key = provider_info.get("env_key", "")
        
        if not os.environ.get(env_key):
            return f"Missing API key for {provider_info['name']}. Set {env_key} in your .env file."
        
        # Check Replicate API key for image generation
        if not os.environ.get("REPLICATE_API_TOKEN"):
            return "Missing REPLICATE_API_TOKEN for image generation. Set it in your .env file."
        
        return None
        
    except ConfigError as e:
        return str(e)
    except Exception as e:
        return f"Configuration error: {str(e)}"


def render_run_controls(settings: Dict, scene: Dict):
    """Render the run controls and status."""
    st.markdown("---")
    
    config_dict = build_config_dict(settings, scene)
    
    # Validate button
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("✅ Validate Config", use_container_width=True):
            error = validate_configuration(config_dict)
            if error:
                st.error(f"❌ {error}")
            else:
                st.success("✅ Configuration is valid!")
    
    with col2:
        if st.button("💾 Export Config", use_container_width=True):
            # Create downloadable JSON
            config_json = json.dumps(config_dict, indent=2)
            st.download_button(
                label="📥 Download JSON",
                data=config_json,
                file_name=f"{settings['project_name']}_config.json",
                mime="application/json",
            )
    
    with col3:
        # Main run button
        is_running = st.session_state.get("running", False)
        
        if is_running:
            st.button("⏳ Running...", disabled=True, use_container_width=True)
            
            # Show progress
            progress = st.session_state.get("progress", 0.0)
            st.progress(progress)
            st.caption(st.session_state.get("current_step", "Initializing..."))
        else:
            if st.button("🚀 Start Pipeline", type="primary", use_container_width=True):
                error = validate_configuration(config_dict)
                if error:
                    st.error(f"❌ {error}")
                else:
                    run_pipeline(config_dict)


def run_pipeline(config_dict: Dict):
    """Run the StarStitch pipeline with the given configuration."""
    st.session_state.running = True
    st.session_state.error = None
    st.session_state.output_video = None
    st.session_state.logs = []
    
    try:
        # Create configuration
        config = StarStitchConfig.from_dict(config_dict)
        
        # Set up logging to capture in UI
        logger = logging.getLogger("StarStitch-UI")
        logger.setLevel(logging.INFO)
        
        # Create file manager
        file_manager = FileManager(
            base_output_folder=config.output_folder,
            project_name=config.project_name,
            logger=logger,
        )
        file_manager.create_render_folder()
        
        # Initialize providers
        st.session_state.current_step = "Initializing providers..."
        st.session_state.progress = 0.05
        
        image_generator = ImageGenerator(
            model=config.settings.image_model,
            logger=logger,
        )
        
        video_generator = create_video_generator(
            provider=config.settings.video_provider,
            model=config.settings.video_model,
            logger=logger,
        )
        
        st.session_state.logs.append(f"Using video provider: {video_generator.provider_name}")
        
        # Initialize FFmpeg
        ffmpeg = FFmpegUtils(logger=logger)
        if not ffmpeg.check_availability():
            raise RuntimeError("FFmpeg is not available. Please install FFmpeg.")
        
        # Process sequence
        total_steps = len(config.sequence) * 3 + 1  # images + videos + frames + concat
        current_step = 0
        
        # Generate anchor image
        st.session_state.current_step = f"Generating anchor image: {config.anchor.name}"
        anchor_path = file_manager.get_anchor_image_path(config.anchor.name)
        
        prompt = config.get_combined_prompt(config.anchor.visual_prompt)
        image_generator.generate(
            prompt=prompt,
            output_path=anchor_path,
            aspect_ratio=config.settings.aspect_ratio,
        )
        
        current_step += 1
        st.session_state.progress = current_step / total_steps
        st.session_state.logs.append(f"✓ Generated anchor: {config.anchor.name}")
        
        # Track current start frame
        current_start = anchor_path
        
        # Process each target
        for i, target in enumerate(config.targets, start=1):
            # Generate target image
            st.session_state.current_step = f"Generating target image: {target.name}"
            target_path = file_manager.get_target_image_path(i, target.name)
            
            prompt = config.get_combined_prompt(target.visual_prompt)
            image_generator.generate(
                prompt=prompt,
                output_path=target_path,
                aspect_ratio=config.settings.aspect_ratio,
            )
            
            current_step += 1
            st.session_state.progress = current_step / total_steps
            st.session_state.logs.append(f"✓ Generated target: {target.name}")
            
            # Generate morph video
            st.session_state.current_step = f"Generating morph video to {target.name}..."
            morph_path = file_manager.get_morph_video_path(i, target.name)
            
            video_generator.generate(
                start_image_path=current_start,
                end_image_path=target_path,
                output_path=morph_path,
                prompt="smooth morphing transition between two people",
                duration=config.settings.transition_duration,
                aspect_ratio=config.settings.aspect_ratio,
            )
            
            current_step += 1
            st.session_state.progress = current_step / total_steps
            st.session_state.logs.append(f"✓ Generated morph video: {morph_path.name}")
            
            # Extract last frame
            st.session_state.current_step = f"Extracting frame from {target.name} video..."
            lastframe_path = file_manager.get_lastframe_path(i, target.name)
            ffmpeg.extract_last_frame(morph_path, lastframe_path)
            
            current_step += 1
            st.session_state.progress = current_step / total_steps
            
            # Update start frame for next iteration
            current_start = lastframe_path
        
        # Concatenate final video
        st.session_state.current_step = "Concatenating final video..."
        
        video_paths = file_manager.list_morph_videos()
        final_path = file_manager.get_final_output_path()
        
        ffmpeg.concatenate_videos(
            video_paths=video_paths,
            output_path=final_path,
            filelist_path=file_manager.get_filelist_path(),
        )
        
        st.session_state.progress = 1.0
        st.session_state.current_step = "Complete!"
        st.session_state.output_video = str(final_path)
        st.session_state.logs.append(f"🎉 Final video saved: {final_path}")
        
    except Exception as e:
        st.session_state.error = str(e)
        st.session_state.logs.append(f"❌ Error: {str(e)}")
    
    finally:
        st.session_state.running = False


def render_output_section():
    """Render the output/results section."""
    if st.session_state.get("output_video"):
        st.markdown("### 🎬 Output")
        
        video_path = st.session_state.output_video
        if Path(video_path).exists():
            st.video(video_path)
            
            # Download button
            with open(video_path, "rb") as f:
                st.download_button(
                    label="📥 Download Video",
                    data=f,
                    file_name=Path(video_path).name,
                    mime="video/mp4",
                )
    
    if st.session_state.get("error"):
        st.error(f"❌ Pipeline Error: {st.session_state.error}")
    
    if st.session_state.get("logs"):
        with st.expander("📋 Logs", expanded=False):
            for log in st.session_state.logs:
                st.text(log)


def render_sidebar():
    """Render the sidebar with info and quick actions."""
    with st.sidebar:
        st.markdown("## 📖 Quick Guide")
        
        st.markdown("""
        **1. Select Provider**
        Choose your video generation backend
        
        **2. Configure Scene**
        Set the location and style for all images
        
        **3. Add Subjects**
        Define the people/characters to morph between
        
        **4. Run Pipeline**
        Generate images, morph videos, and final output
        """)
        
        st.markdown("---")
        
        st.markdown("## 🔑 API Keys")
        
        # Check API key status
        keys = [
            ("REPLICATE_API_TOKEN", "Replicate (Images)"),
            ("FAL_KEY", "Fal.ai (Kling)"),
            ("RUNWAY_API_KEY", "Runway ML"),
            ("LUMA_API_KEY", "Luma AI"),
        ]
        
        for env_var, name in keys:
            has_key = bool(os.environ.get(env_var))
            icon = "✅" if has_key else "⚠️"
            st.markdown(f"{icon} {name}")
        
        st.markdown("""
        <div style='font-size: 0.8rem; color: #888; margin-top: 1rem;'>
        Configure API keys in your <code>.env</code> file
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown("## 🔗 Resources")
        st.markdown("""
        - [Fal.ai Console](https://fal.ai)
        - [Runway ML](https://runwayml.com)
        - [Luma AI](https://lumalabs.ai)
        - [Replicate](https://replicate.com)
        """)


def main():
    """Main application entry point."""
    init_session_state()
    
    render_header()
    render_sidebar()
    
    # Main content
    render_provider_selector()
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        settings = render_settings_panel()
        scene = render_scene_settings()
    
    with col2:
        render_sequence_editor()
    
    render_run_controls(settings, scene)
    render_output_section()


if __name__ == "__main__":
    main()
