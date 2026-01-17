#!/usr/bin/env python3
"""
StarStitch - AI Video Morphing Pipeline
========================================

Generates seamless "morphing selfie" video chains by combining
AI image generation with video morphing technology.

Usage:
    python main.py                          # Standard run with config.json
    python main.py --config custom.json     # Use custom config file
    python main.py --resume renders/render_XXX  # Resume crashed render
    python main.py --dry-run                # Validate config without API calls
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table

from config import ConfigLoader, StarStitchConfig, ConfigError
from providers import ImageGenerator, VideoGenerator
from providers.base_provider import ImageGenerationError, VideoGenerationError
from utils import FileManager, FFmpegUtils, StateManager
from utils.ffmpeg_utils import FFmpegError
from utils.state_manager import StepStatus


# Initialize Rich console for beautiful output
console = Console()


class ChainManager:
    """
    Core orchestrator for the StarStitch pipeline.
    
    Manages the complete workflow:
    1. Generate anchor image
    2. Loop through sequence generating targets, morphs, and extracting frames
    3. Concatenate final video
    
    Implements crash recovery through state management.
    """

    def __init__(
        self,
        config: StarStitchConfig,
        logger: logging.Logger,
        dry_run: bool = False,
    ):
        """
        Initialize the chain manager.
        
        Args:
            config: Validated pipeline configuration.
            logger: Logger instance for output.
            dry_run: If True, validate but don't make API calls.
        """
        self.config = config
        self.logger = logger
        self.dry_run = dry_run

        # Initialize utilities
        self.file_manager = FileManager(
            base_output_folder=config.output_folder,
            project_name=config.project_name,
            logger=logger,
        )
        self.ffmpeg = FFmpegUtils(logger=logger)

        # Initialize providers (only if not dry run)
        if not dry_run:
            self.image_generator = ImageGenerator(
                model=config.settings.image_model,
                logger=logger,
            )
            self.video_generator = VideoGenerator(
                model=config.settings.video_model,
                logger=logger,
            )
        else:
            self.image_generator = None
            self.video_generator = None

        # State manager will be initialized when render folder is created
        self.state_manager: Optional[StateManager] = None

        # Tracking
        self.start_time: Optional[float] = None
        self.total_cost: float = 0.0

    def run(self) -> Path:
        """
        Execute the complete pipeline.
        
        Returns:
            Path to the final output video.
            
        Raises:
            Various exceptions on pipeline failure.
        """
        self.start_time = time.time()

        console.print(Panel.fit(
            f"[bold cyan]StarStitch Pipeline[/bold cyan]\n"
            f"Project: {self.config.project_name}\n"
            f"Subjects: {len(self.config.sequence)}",
            title="Starting",
            border_style="cyan",
        ))

        try:
            # Phase 1: Initialization
            self._phase_initialization()

            if self.dry_run:
                console.print("[green]Dry run completed successfully![/green]")
                console.print("Configuration is valid. Ready to run.")
                return self.file_manager.get_final_output_path()

            # Phase 2: Generate anchor image
            self._phase_anchor()

            # Phase 3: Recursive loop for each target
            self._phase_transitions()

            # Phase 4: Final assembly
            final_path = self._phase_assembly()

            # Report completion
            self._report_completion(final_path)

            return final_path

        except KeyboardInterrupt:
            self.logger.warning("Pipeline interrupted by user")
            console.print("\n[yellow]Pipeline interrupted. Progress has been saved.[/yellow]")
            console.print(f"Resume with: python main.py --resume {self.file_manager.render_folder}")
            raise

        except Exception as e:
            self.logger.exception(f"Pipeline failed: {e}")
            if self.state_manager:
                console.print(f"\n[red]Pipeline failed: {e}[/red]")
                console.print(f"Resume with: python main.py --resume {self.file_manager.render_folder}")
            raise

    def resume(self, render_folder: Path) -> Path:
        """
        Resume a previously interrupted pipeline.
        
        Args:
            render_folder: Path to the existing render folder.
            
        Returns:
            Path to the final output video.
        """
        self.start_time = time.time()

        console.print(Panel.fit(
            f"[bold yellow]Resuming Pipeline[/bold yellow]\n"
            f"Folder: {render_folder}",
            title="Resume",
            border_style="yellow",
        ))

        # Set up file manager with existing folder
        self.file_manager.set_render_folder(render_folder)

        # Load existing state
        self.state_manager = StateManager(
            state_file_path=self.file_manager.get_state_file_path(),
            logger=self.logger,
        )
        self.state_manager.load()

        # Validate config hash
        if self.state_manager.state.config_hash != self.config.config_hash:
            self.logger.warning(
                "Configuration has changed since last run. "
                "This may cause unexpected results."
            )

        # Find resume point
        resume_index = self.state_manager.get_resume_point()
        if resume_index is None:
            console.print("[green]Pipeline already completed![/green]")
            return Path(self.state_manager.state.final_output)

        console.print(f"Resuming from step {resume_index + 1}")
        console.print(self.state_manager.get_progress_summary())

        # Resume the pipeline phases
        # Check if we need to redo any incomplete steps
        self._resume_transitions()

        # Final assembly
        final_path = self._phase_assembly()

        self._report_completion(final_path)

        return final_path

    def _phase_initialization(self) -> None:
        """Phase 1: Initialize render folder and state."""
        self.logger.info("Phase 1: Initialization")

        # Check FFMPEG availability
        if not self.ffmpeg.check_availability():
            raise RuntimeError("FFMPEG is not available. Please install FFMPEG.")

        # Create render folder
        self.file_manager.create_render_folder()

        # Set up logging to file
        self._setup_file_logging()

        # Initialize state manager
        self.state_manager = StateManager(
            state_file_path=self.file_manager.get_state_file_path(),
            logger=self.logger,
        )
        self.state_manager.initialize(
            project_name=self.config.project_name,
            render_folder=self.file_manager.render_folder,
            config_hash=self.config.config_hash,
            sequence_length=len(self.config.sequence),
        )

        # Log configuration summary
        self.logger.info(f"Configuration:\n{self.config.summary()}")

        console.print(f"[dim]Output folder: {self.file_manager.render_folder}[/dim]")

    def _phase_anchor(self) -> None:
        """Phase 2: Generate the anchor (first) image."""
        self.logger.info("Phase 2: Generating anchor image")

        anchor = self.config.anchor
        step_id = f"anchor_{anchor.id}"

        # Add step to state
        self.state_manager.add_step(
            step_id=step_id,
            step_type="anchor",
            subject_name=anchor.name,
            index=0,
        )

        # Check if already completed (resume case)
        if self.state_manager.is_step_completed(step_id):
            self.logger.info(f"Anchor image already exists, skipping")
            anchor_path = self.file_manager.get_anchor_image_path(anchor.name)
            self.state_manager.update_current_start_frame(anchor_path)
            return

        self.state_manager.start_step(step_id)

        with console.status(f"[bold green]Generating anchor image: {anchor.name}..."):
            prompt = self.config.get_combined_prompt(anchor.visual_prompt)
            output_path = self.file_manager.get_anchor_image_path(anchor.name)

            start_time = time.time()

            self.image_generator.generate(
                prompt=prompt,
                output_path=output_path,
                aspect_ratio=self.config.settings.aspect_ratio,
            )

            duration = time.time() - start_time

        self.state_manager.complete_step(step_id, output_path, duration)
        self.state_manager.update_current_start_frame(output_path)

        console.print(f"[green]✓[/green] Anchor image generated: {output_path.name}")

    def _phase_transitions(self) -> None:
        """Phase 3: Generate target images, morph videos, and extract frames."""
        self.logger.info("Phase 3: Generating transitions")

        targets = self.config.targets

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Processing subjects...", total=len(targets))

            for i, target in enumerate(targets, start=1):
                progress.update(task, description=f"Processing: {target.name}")

                self._process_single_target(i, target)

                progress.advance(task)

    def _process_single_target(self, index: int, target) -> None:
        """
        Process a single target: generate image, create morph, extract frame.
        
        Args:
            index: 1-based sequence index.
            target: SubjectConfig for this target.
        """
        self.logger.info(f"Processing target {index}: {target.name}")

        # Step A: Generate target image
        target_path = self._generate_target_image(index, target)

        # Step B: Generate morph video
        morph_path = self._generate_morph_video(index, target, target_path)

        # Step C: Extract last frame
        lastframe_path = self._extract_last_frame(index, target, morph_path)

        # Step D: Update state - use extracted frame as next start
        self.state_manager.update_current_start_frame(lastframe_path)
        self.logger.info(f"Updated start frame for next iteration: {lastframe_path.name}")

    def _generate_target_image(self, index: int, target) -> Path:
        """Generate the target image for this subject."""
        step_id = f"target_{index}_{target.id}"

        self.state_manager.add_step(
            step_id=step_id,
            step_type="target",
            subject_name=target.name,
            index=index,
        )

        output_path = self.file_manager.get_target_image_path(index, target.name)

        if self.state_manager.is_step_completed(step_id) and output_path.exists():
            self.logger.info(f"Target image exists, skipping: {output_path.name}")
            return output_path

        self.state_manager.start_step(step_id)

        try:
            prompt = self.config.get_combined_prompt(target.visual_prompt)
            start_time = time.time()

            self.image_generator.generate(
                prompt=prompt,
                output_path=output_path,
                aspect_ratio=self.config.settings.aspect_ratio,
            )

            duration = time.time() - start_time
            self.state_manager.complete_step(step_id, output_path, duration)

            console.print(f"  [green]✓[/green] Target image: {output_path.name}")
            return output_path

        except ImageGenerationError as e:
            self.state_manager.fail_step(step_id, str(e))
            raise

    def _generate_morph_video(self, index: int, target, target_path: Path) -> Path:
        """Generate the morph video between current start frame and target."""
        step_id = f"morph_{index}_{target.id}"

        self.state_manager.add_step(
            step_id=step_id,
            step_type="morph",
            subject_name=target.name,
            index=index,
        )

        output_path = self.file_manager.get_morph_video_path(index, target.name)

        if self.state_manager.is_step_completed(step_id) and output_path.exists():
            self.logger.info(f"Morph video exists, skipping: {output_path.name}")
            return output_path

        self.state_manager.start_step(step_id)

        try:
            # Get the current start frame (anchor or previous last frame)
            start_frame = self.state_manager.get_current_start_frame()
            if start_frame is None:
                raise RuntimeError("No start frame available for morph generation")

            start_time = time.time()

            self.video_generator.generate(
                start_image_path=start_frame,
                end_image_path=target_path,
                output_path=output_path,
                prompt="smooth morphing transition between two people",
                duration=self.config.settings.transition_duration,
                aspect_ratio=self.config.settings.aspect_ratio,
            )

            duration = time.time() - start_time
            self.state_manager.complete_step(step_id, output_path, duration)

            console.print(f"  [green]✓[/green] Morph video: {output_path.name}")
            return output_path

        except VideoGenerationError as e:
            self.state_manager.fail_step(step_id, str(e))
            raise

    def _extract_last_frame(self, index: int, target, video_path: Path) -> Path:
        """Extract the last frame from the morph video."""
        step_id = f"lastframe_{index}_{target.id}"

        self.state_manager.add_step(
            step_id=step_id,
            step_type="lastframe",
            subject_name=target.name,
            index=index,
        )

        output_path = self.file_manager.get_lastframe_path(index, target.name)

        if self.state_manager.is_step_completed(step_id) and output_path.exists():
            self.logger.info(f"Last frame exists, skipping: {output_path.name}")
            return output_path

        self.state_manager.start_step(step_id)

        try:
            start_time = time.time()

            self.ffmpeg.extract_last_frame(video_path, output_path)

            duration = time.time() - start_time
            self.state_manager.complete_step(step_id, output_path, duration)

            console.print(f"  [green]✓[/green] Last frame: {output_path.name}")
            return output_path

        except FFmpegError as e:
            self.state_manager.fail_step(step_id, str(e))
            raise

    def _resume_transitions(self) -> None:
        """Resume transitions from the last incomplete step."""
        # Find where we left off based on state
        for i, target in enumerate(self.config.targets, start=1):
            # Check each step for this target
            target_step_id = f"target_{i}_{target.id}"
            morph_step_id = f"morph_{i}_{target.id}"
            lastframe_step_id = f"lastframe_{i}_{target.id}"

            # If target not complete, process full target
            if not self.state_manager.is_step_completed(target_step_id):
                self._process_single_target(i, target)
                continue

            # If morph not complete, continue from there
            target_path = self.file_manager.get_target_image_path(i, target.name)
            if not self.state_manager.is_step_completed(morph_step_id):
                morph_path = self._generate_morph_video(i, target, target_path)
                lastframe_path = self._extract_last_frame(i, target, morph_path)
                self.state_manager.update_current_start_frame(lastframe_path)
                continue

            # If lastframe not complete, continue from there
            morph_path = self.file_manager.get_morph_video_path(i, target.name)
            if not self.state_manager.is_step_completed(lastframe_step_id):
                lastframe_path = self._extract_last_frame(i, target, morph_path)
                self.state_manager.update_current_start_frame(lastframe_path)

    def _phase_assembly(self) -> Path:
        """Phase 4: Concatenate all morph videos into final output."""
        self.logger.info("Phase 4: Final assembly")

        step_id = "concat_final"

        # Check if this step was already added
        existing_step = None
        for step in self.state_manager.state.steps:
            if step.step_id == step_id:
                existing_step = step
                break

        if existing_step is None:
            self.state_manager.add_step(
                step_id=step_id,
                step_type="concat",
                subject_name="final",
                index=len(self.config.sequence),
            )

        output_path = self.file_manager.get_final_output_path()

        if self.state_manager.is_step_completed(step_id) and output_path.exists():
            self.logger.info(f"Final video exists, skipping concatenation")
            return output_path

        self.state_manager.start_step(step_id)

        with console.status("[bold green]Concatenating final video..."):
            try:
                video_paths = self.file_manager.list_morph_videos()

                if not video_paths:
                    raise RuntimeError("No morph videos found for concatenation")

                self.logger.info(f"Concatenating {len(video_paths)} videos")

                start_time = time.time()

                self.ffmpeg.concatenate_videos(
                    video_paths=video_paths,
                    output_path=output_path,
                    filelist_path=self.file_manager.get_filelist_path(),
                )

                duration = time.time() - start_time
                self.state_manager.complete_step(step_id, output_path, duration)

                # Mark pipeline as complete
                self.state_manager.mark_completed(output_path)

                return output_path

            except FFmpegError as e:
                self.state_manager.fail_step(step_id, str(e))
                raise

    def _setup_file_logging(self) -> None:
        """Add file handler for logging to render folder."""
        log_path = self.file_manager.get_log_file_path()
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        self.logger.addHandler(file_handler)
        self.logger.info(f"Logging to: {log_path}")

    def _report_completion(self, final_path: Path) -> None:
        """Report pipeline completion with summary."""
        total_time = time.time() - self.start_time

        # Get video duration
        try:
            video_duration = self.ffmpeg.get_video_duration(final_path)
        except FFmpegError:
            video_duration = 0

        # Get file size
        file_size_mb = final_path.stat().st_size / (1024 * 1024) if final_path.exists() else 0

        # Create summary table
        table = Table(title="Pipeline Complete", show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Final Output", str(final_path))
        table.add_row("Video Duration", f"{video_duration:.1f} seconds")
        table.add_row("File Size", f"{file_size_mb:.1f} MB")
        table.add_row("Total Time", f"{total_time:.1f} seconds")
        table.add_row("Subjects Processed", str(len(self.config.sequence)))

        console.print()
        console.print(table)
        console.print()
        console.print("[bold green]🎉 StarStitch complete![/bold green]")


def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Set up logging with Rich handler.
    
    Args:
        verbose: Enable debug-level logging.
        
    Returns:
        Configured logger instance.
    """
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                show_time=True,
                show_path=verbose,
            )
        ],
    )

    return logging.getLogger("StarStitch")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="StarStitch - AI Video Morphing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                              Standard run with config.json
  python main.py --config custom.json         Use custom config file
  python main.py --resume renders/render_XXX  Resume crashed render
  python main.py --dry-run                    Validate config only
  python main.py -v                           Verbose logging
        """,
    )

    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=Path("config.json"),
        help="Path to configuration file (default: config.json)",
    )

    parser.add_argument(
        "--resume",
        "-r",
        type=Path,
        help="Resume from an existing render folder",
    )

    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Validate configuration without making API calls",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose (debug) logging",
    )

    return parser.parse_args()


def main() -> int:
    """
    Main entry point for StarStitch.
    
    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    # Load environment variables
    load_dotenv()

    # Parse arguments
    args = parse_arguments()

    # Set up logging
    logger = setup_logging(verbose=args.verbose)

    try:
        # Load configuration
        config_loader = ConfigLoader(logger=logger)
        config = config_loader.load(args.config)

        # Print configuration summary
        if args.verbose:
            console.print(Panel(config.summary(), title="Configuration", border_style="blue"))

        # Create chain manager
        chain_manager = ChainManager(
            config=config,
            logger=logger,
            dry_run=args.dry_run,
        )

        # Execute pipeline
        if args.resume:
            final_path = chain_manager.resume(args.resume)
        else:
            final_path = chain_manager.run()

        logger.info(f"Output: {final_path}")
        return 0

    except ConfigError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        return 1

    except FileNotFoundError as e:
        console.print(f"[red]File Not Found:[/red] {e}")
        return 1

    except (ImageGenerationError, VideoGenerationError) as e:
        console.print(f"[red]Generation Error:[/red] {e}")
        return 2

    except FFmpegError as e:
        console.print(f"[red]FFMPEG Error:[/red] {e}")
        if e.stderr:
            console.print(f"[dim]Details: {e.stderr[:500]}[/dim]")
        return 3

    except KeyboardInterrupt:
        return 130  # Standard exit code for SIGINT

    except Exception as e:
        console.print(f"[red]Unexpected Error:[/red] {e}")
        logger.exception("Unhandled exception")
        return 99


if __name__ == "__main__":
    sys.exit(main())
