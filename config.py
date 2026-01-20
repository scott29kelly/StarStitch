"""
Configuration loader and validator for StarStitch.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import field
from dataclasses import dataclass, field

# Re-export AudioSettings for external use
__all__ = ['Subject', 'GlobalScene', 'AudioSettings', 'Settings', 'StarStitchConfig']


@dataclass
class Subject:
    """A subject in the morph sequence."""
    id: str
    name: str
    visual_prompt: str


@dataclass
class GlobalScene:
    """Global scene settings applied to all images."""
    location_prompt: str = ""
    negative_prompt: str = "blurry, distorted, cartoon, low quality"


@dataclass
class AudioSettings:
    """Audio configuration for background music."""
    enabled: bool = False
    audio_path: str = ""
    volume: float = 0.8  # 0.0 to 1.0
    fade_in_sec: float = 1.0  # Fade in duration at start
    fade_out_sec: float = 2.0  # Fade out duration at end
    loop: bool = True  # Loop audio if shorter than video
    normalize: bool = True  # Normalize audio volume
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioSettings":
        """Create AudioSettings from dictionary."""
        return cls(
            enabled=data.get("enabled", False),
            audio_path=data.get("audio_path", ""),
            volume=data.get("volume", 0.8),
            fade_in_sec=data.get("fade_in_sec", 1.0),
            fade_out_sec=data.get("fade_out_sec", 2.0),
            loop=data.get("loop", True),
            normalize=data.get("normalize", True)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "audio_path": self.audio_path,
            "volume": self.volume,
            "fade_in_sec": self.fade_in_sec,
            "fade_out_sec": self.fade_out_sec,
            "loop": self.loop,
            "normalize": self.normalize
        }


@dataclass
class Settings:
    """Generation settings."""
    aspect_ratio: str = "9:16"
    transition_duration_sec: int = 5
    image_model: str = "black-forest-labs/flux-1.1-pro"
    video_provider: str = "replicate"  # "replicate" (Veo 3.1 Fast ~1min), "fal" (Kling, slow)
    video_model: str = ""  # Optional model override, empty uses provider default
    variants: List[str] = None  # Output variants like ["16:9", "1:1"]

    def __post_init__(self):
        if self.variants is None:
            self.variants = []


@dataclass
class StarStitchConfig:
    """Complete StarStitch configuration."""
    project_name: str
    output_folder: str
    settings: Settings
    global_scene: GlobalScene
    sequence: List[Subject]
    audio: Optional[AudioSettings] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StarStitchConfig":
        """Create config from dictionary."""
        settings_data = data.get("settings", {})
        settings = Settings(
            aspect_ratio=settings_data.get("aspect_ratio", "9:16"),
            transition_duration_sec=settings_data.get("transition_duration_sec", 5),
            image_model=settings_data.get("image_model", "black-forest-labs/flux-1.1-pro"),
            video_provider=settings_data.get("video_provider", "replicate"),
            video_model=settings_data.get("video_model", ""),
            variants=settings_data.get("variants", [])
        )
        
        scene_data = data.get("global_scene", {})
        global_scene = GlobalScene(
            location_prompt=scene_data.get("location_prompt", ""),
            negative_prompt=scene_data.get("negative_prompt", "")
        )
        
        sequence = [
            Subject(
                id=s.get("id", f"subject_{i}"),
                name=s.get("name", f"Subject {i+1}"),
                visual_prompt=s.get("visual_prompt", "")
            )
            for i, s in enumerate(data.get("sequence", []))
        ]
        
        # Parse audio settings if present
        audio_data = data.get("audio")
        audio = AudioSettings.from_dict(audio_data) if audio_data else None
        
        return cls(
            project_name=data.get("project_name", "untitled"),
            output_folder=data.get("output_folder", "renders"),
            settings=settings,
            global_scene=global_scene,
            sequence=sequence,
            audio=audio
        )
    
    @classmethod
    def from_file(cls, path: str) -> "StarStitchConfig":
        """Load config from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        result = {
            "project_name": self.project_name,
            "output_folder": self.output_folder,
            "settings": {
                "aspect_ratio": self.settings.aspect_ratio,
                "transition_duration_sec": self.settings.transition_duration_sec,
                "image_model": self.settings.image_model,
                "video_provider": self.settings.video_provider,
                "video_model": self.settings.video_model,
                "variants": self.settings.variants
            },
            "global_scene": {
                "location_prompt": self.global_scene.location_prompt,
                "negative_prompt": self.global_scene.negative_prompt
            },
            "sequence": [
                {
                    "id": s.id,
                    "name": s.name,
                    "visual_prompt": s.visual_prompt
                }
                for s in self.sequence
            ]
        }
        
        # Include audio settings if configured
        if self.audio:
            result["audio"] = self.audio.to_dict()
        
        return result
    
    def to_file(self, path: str) -> None:
        """Save config to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def validate(self) -> List[str]:
        """
        Validate the configuration.
        
        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []
        
        if not self.project_name:
            errors.append("Project name is required")
        
        if len(self.sequence) < 2:
            errors.append("At least 2 subjects are required for morphing")
        
        if not self.global_scene.location_prompt:
            errors.append("Location prompt is required")
        
        for i, subject in enumerate(self.sequence):
            if not subject.name:
                errors.append(f"Subject {i+1} is missing a name")
            if not subject.visual_prompt:
                errors.append(f"Subject '{subject.name}' is missing a visual prompt")
        
        valid_ratios = ["9:16", "16:9", "1:1", "4:3", "3:4", "4:5"]
        if self.settings.aspect_ratio not in valid_ratios:
            errors.append(f"Invalid aspect ratio. Must be one of: {valid_ratios}")
        
        # Validate variants if specified
        if self.settings.variants:
            for variant in self.settings.variants:
                if variant not in valid_ratios:
                    errors.append(f"Invalid variant ratio '{variant}'. Must be one of: {valid_ratios}")
        
        if not 2 <= self.settings.transition_duration_sec <= 10:
            errors.append("Transition duration must be between 2 and 10 seconds")
        
        # Validate audio settings if enabled
        if self.audio and self.audio.enabled:
            if not self.audio.audio_path:
                errors.append("Audio path is required when audio is enabled")
            elif not Path(self.audio.audio_path).exists():
                errors.append(f"Audio file not found: {self.audio.audio_path}")
            
            if not 0.0 <= self.audio.volume <= 1.0:
                errors.append("Audio volume must be between 0.0 and 1.0")
            
            if self.audio.fade_in_sec < 0:
                errors.append("Audio fade in duration cannot be negative")
            
            if self.audio.fade_out_sec < 0:
                errors.append("Audio fade out duration cannot be negative")
        
        return errors
