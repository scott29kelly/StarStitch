#!/usr/bin/env python3
"""
StarStitch - AI-Powered Video Morphing Pipeline
Main entry point for CLI-based generation.

Usage:
    python main.py                          # Use default config.json
    python main.py --config custom.json     # Use custom config
    python main.py --resume renders/render_20250117_143022  # Resume a crashed render
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional, Callable

from dotenv import load_dotenv

from providers import ImageGenerator, VideoGenerator
from utils import FFmpegUtils, FileManager, AudioUtils

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


class StarStitchPipeline:
    """
    Main orchestrator for the StarStitch video morphing pipeline.
    
    Coordinates:
    - Image generation for each subject
    - Video morphing between subjects
    - Frame extraction for seamless transitions
    - Final video concatenation
    """
    
    def __init__(
        self,
        config: dict,
        on_progress: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize the pipeline.
        
        Args:
            config: Configuration dictionary.
            on_progress: Optional callback for progress updates.
        """
        self.config = config
        self.on_progress = on_progress or (lambda msg: logger.info(msg))
        
        # Extract settings
        settings = config.get("settings", {})
        
        # Initialize components
        self.image_gen = ImageGenerator(
            model=settings.get("image_model", "black-forest-labs/flux-1.1-pro")
        )
        self.video_gen = VideoGenerator(
            model=settings.get("video_model", "fal-ai/kling-video/v1.6/pro/image-to-video")
        )
        self.ffmpeg = FFmpegUtils()
        self.audio_utils = AudioUtils()
        self.file_manager = FileManager(
            base_output_dir=config.get("output_folder", "renders"),
            project_name=config.get("project_name", "starstitch")
        )
        
        # Pipeline state
        self.sequence = config.get("sequence", [])
        self.global_scene = config.get("global_scene", {})
        self.aspect_ratio = settings.get("aspect_ratio", "9:16")
        self.transition_duration = settings.get("transition_duration_sec", 5)
        
        # Audio configuration
        self.audio_config = config.get("audio", {})
        self.audio_enabled = self.audio_config.get("enabled", False)
    
    def run(self, resume_dir: Optional[Path] = None) -> Path:
        """
        Execute the full pipeline.
        
        Args:
            resume_dir: Optional path to resume a previous render.
            
        Returns:
            Path to the final output video.
        """
        # Initialize or resume session
        if resume_dir:
            self.on_progress(f"Resuming from {resume_dir}...")
            self.file_manager.load_session(resume_dir)
        else:
            self.on_progress("Creating new render session...")
            self.file_manager.create_render_session()
            self.file_manager.save_config(self.config)
        
        # Calculate total steps: images + videos
        num_subjects = len(self.sequence)
        num_morphs = max(0, num_subjects - 1)
        total_steps = num_subjects + num_morphs
        
        self.file_manager.set_total_steps(total_steps)
        self.file_manager.set_status("running")
        
        self.on_progress(f"Pipeline started: {num_subjects} subjects, {num_morphs} morphs")
        
        try:
            # Step 1: Generate all subject images
            self._generate_images()
            
            # Step 2: Generate morph videos
            self._generate_morphs()
            
            # Step 3: Concatenate final video
            final_path = self._concatenate_final()
            
            # Step 4: Add audio track if configured
            if self.audio_enabled:
                final_path = self._add_audio_track(final_path)
            
            self.file_manager.set_status("complete")
            self.on_progress(f"Pipeline complete! Output: {final_path}")
            
            return final_path
            
        except Exception as e:
            self.file_manager.set_status("error", str(e))
            logger.error(f"Pipeline failed: {e}")
            raise
    
    def _generate_images(self) -> None:
        """Generate images for all subjects in the sequence."""
        self.on_progress("=== Phase 1: Generating Subject Images ===")
        
        location_prompt = self.global_scene.get("location_prompt", "")
        negative_prompt = self.global_scene.get("negative_prompt", "")
        
        for i, subject in enumerate(self.sequence):
            step_type = "image"
            
            # Check if already complete (for resume)
            if self.file_manager.is_step_complete(i, step_type):
                self.on_progress(f"Skipping {subject['name']} (already generated)")
                continue
            
            # Determine output path
            if i == 0:
                output_path = self.file_manager.get_image_path(0, "anchor")
            else:
                output_path = self.file_manager.get_image_path(i, "target")
            
            self.on_progress(f"Generating [{i+1}/{len(self.sequence)}]: {subject['name']}")
            
            # Generate image
            self.image_gen.generate_subject(
                subject_name=subject["name"],
                visual_prompt=subject.get("visual_prompt", ""),
                location_prompt=location_prompt,
                negative_prompt=negative_prompt,
                aspect_ratio=self.aspect_ratio,
                output_path=output_path,
                on_progress=self.on_progress
            )
            
            self.file_manager.mark_step_complete(i, step_type, output_path, {
                "subject": subject["name"]
            })
    
    def _generate_morphs(self) -> None:
        """Generate morph transition videos between consecutive subjects."""
        self.on_progress("=== Phase 2: Generating Morph Transitions ===")
        
        if len(self.sequence) < 2:
            self.on_progress("Not enough subjects for morphing. Skipping.")
            return
        
        # The "glitch fix" loop:
        # 1. Start with anchor image
        # 2. Generate morph to target
        # 3. Extract LAST FRAME of morph video
        # 4. Use extracted frame as next start (not original target!)
        
        current_start_frame = self.file_manager.get_image_path(0, "anchor")
        
        for i in range(1, len(self.sequence)):
            step_type = "video"
            
            # Check if already complete
            if self.file_manager.is_step_complete(i, step_type):
                # Load the last frame for the next iteration
                last_frame_path = self.file_manager.get_image_path(i, "lastframe")
                if last_frame_path.exists():
                    current_start_frame = last_frame_path
                self.on_progress(f"Skipping morph {i} (already generated)")
                continue
            
            target_image = self.file_manager.get_image_path(i, "target")
            output_video = self.file_manager.get_video_path(i)
            
            self.on_progress(f"Creating morph [{i}/{len(self.sequence)-1}]: {self.sequence[i-1]['name']} → {self.sequence[i]['name']}")
            
            # Generate morph video
            self.video_gen.create_morph(
                start_image_path=current_start_frame,
                end_image_path=target_image,
                duration_seconds=self.transition_duration,
                aspect_ratio=self.aspect_ratio,
                output_path=output_video,
                on_progress=self.on_progress
            )
            
            self.file_manager.mark_step_complete(i, step_type, output_video)
            
            # Extract last frame for next morph
            last_frame_path = self.file_manager.get_image_path(i, "lastframe")
            self.on_progress(f"Extracting last frame for seamless transition...")
            
            self.ffmpeg.extract_last_frame(output_video, last_frame_path)
            self.file_manager.mark_step_complete(i, "frame", last_frame_path)
            
            # Use extracted frame as next start
            current_start_frame = last_frame_path
    
    def _concatenate_final(self) -> Path:
        """Concatenate all morph videos into the final output."""
        self.on_progress("=== Phase 3: Creating Final Video ===")
        
        video_paths = self.file_manager.get_all_video_paths()
        
        if not video_paths:
            raise RuntimeError("No morph videos found to concatenate")
        
        self.on_progress(f"Concatenating {len(video_paths)} video segments...")
        
        final_path = self.file_manager.get_final_output_path()
        self.ffmpeg.concatenate_videos(video_paths, final_path)
        
        # Get duration for logging
        try:
            duration = self.ffmpeg.get_video_duration(final_path)
            self.on_progress(f"Final video duration: {duration:.1f} seconds")
        except Exception:
            pass
        
        self.file_manager.cleanup_temp_files()
        
        return final_path
    
    def _add_audio_track(self, video_path: Path) -> Path:
        """
        Add background audio track to the final video.
        
        Args:
            video_path: Path to the video file to add audio to.
            
        Returns:
            Path to the video with audio (replaces original if successful).
        """
        self.on_progress("=== Phase 4: Adding Audio Track ===")
        
        audio_path = Path(self.audio_config.get("audio_path", ""))
        
        if not audio_path.exists():
            self.on_progress(f"Warning: Audio file not found: {audio_path}")
            return video_path
        
        if not self.audio_utils.is_supported_format(audio_path):
            self.on_progress(f"Warning: Unsupported audio format: {audio_path.suffix}")
            return video_path
        
        # Get video duration for audio processing
        video_duration = self.ffmpeg.get_video_duration(video_path)
        self.on_progress(f"Video duration: {video_duration:.2f}s")
        
        # Get audio settings
        volume = self.audio_config.get("volume", 0.8)
        fade_in = self.audio_config.get("fade_in_sec", 1.0)
        fade_out = self.audio_config.get("fade_out_sec", 2.0)
        loop = self.audio_config.get("loop", True)
        normalize = self.audio_config.get("normalize", True)
        
        # Prepare audio track (loop/trim, normalize, apply fades)
        processed_audio_path = self.file_manager.render_dir / "processed_audio.aac"
        
        self.on_progress("Processing audio track...")
        self.on_progress(f"  Volume: {volume * 100:.0f}%")
        self.on_progress(f"  Fade in: {fade_in}s, Fade out: {fade_out}s")
        self.on_progress(f"  Loop: {'Yes' if loop else 'No'}, Normalize: {'Yes' if normalize else 'No'}")
        
        try:
            self.audio_utils.prepare_audio_for_video(
                audio_path=audio_path,
                output_path=processed_audio_path,
                video_duration=video_duration,
                volume=volume,
                fade_in_sec=fade_in,
                fade_out_sec=fade_out,
                loop=loop,
                normalize=normalize
            )
            
            # Merge audio with video
            # Create a temp path for the video with audio
            video_with_audio_path = video_path.parent / f"{video_path.stem}_with_audio{video_path.suffix}"
            
            self.on_progress("Merging audio with video...")
            self.ffmpeg.add_audio_to_video(
                video_path=video_path,
                audio_path=processed_audio_path,
                output_path=video_with_audio_path,
                replace_existing=True
            )
            
            # Replace original with audio version
            video_path.unlink(missing_ok=True)
            video_with_audio_path.rename(video_path)
            
            # Clean up processed audio
            processed_audio_path.unlink(missing_ok=True)
            
            self.on_progress(f"Audio track added successfully!")
            
            return video_path
            
        except Exception as e:
            self.on_progress(f"Warning: Failed to add audio track: {e}")
            logger.warning(f"Audio processing failed: {e}")
            # Return the original video without audio
            return video_path


def load_config(config_path: str) -> dict:
    """Load configuration from JSON file."""
    path = Path(config_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(path, "r") as f:
        return json.load(f)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="StarStitch - AI-Powered Video Morphing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Use default config.json
  python main.py --config custom.json     # Use custom config
  python main.py --resume renders/render_20250117_143022
        """
    )
    
    parser.add_argument(
        "--config", "-c",
        default="config.json",
        help="Path to configuration JSON file (default: config.json)"
    )
    
    parser.add_argument(
        "--resume", "-r",
        default=None,
        help="Path to render directory to resume"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # ASCII banner
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🌟  S T A R S T I T C H                                 ║
    ║                                                           ║
    ║   AI-Powered Video Morphing Pipeline                      ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Load config
        logger.info(f"Loading config from: {args.config}")
        config = load_config(args.config)
        
        # Validate minimum requirements
        sequence = config.get("sequence", [])
        if len(sequence) < 2:
            logger.error("At least 2 subjects are required for morphing")
            sys.exit(1)
        
        logger.info(f"Project: {config.get('project_name', 'unnamed')}")
        logger.info(f"Subjects: {len(sequence)}")
        
        # Create and run pipeline
        pipeline = StarStitchPipeline(config)
        
        resume_path = Path(args.resume) if args.resume else None
        final_video = pipeline.run(resume_dir=resume_path)
        
        print(f"\n✅ Success! Final video: {final_video}\n")
        
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
