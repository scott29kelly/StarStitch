"""
Configuration loader and validator for StarStitch.
Handles loading, validation, and access to pipeline configuration.
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


class ConfigError(Exception):
    """Exception for configuration-related errors."""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.field = field


@dataclass
class SubjectConfig:
    """Configuration for a single subject in the sequence."""

    id: str
    name: str
    visual_prompt: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any], index: int) -> "SubjectConfig":
        """
        Create from dictionary with validation.
        
        Args:
            data: Dictionary containing subject configuration.
            index: Index in sequence for error messages.
            
        Returns:
            Validated SubjectConfig instance.
            
        Raises:
            ConfigError: If required fields are missing.
        """
        required_fields = ["id", "name", "visual_prompt"]
        for field_name in required_fields:
            if field_name not in data:
                raise ConfigError(
                    f"Subject at index {index} missing required field: {field_name}",
                    field=f"sequence[{index}].{field_name}",
                )

        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            visual_prompt=str(data["visual_prompt"]),
        )


@dataclass
class SettingsConfig:
    """Pipeline settings configuration."""

    aspect_ratio: str = "9:16"
    transition_duration: str = "5"
    image_model: str = "black-forest-labs/flux-1.1-pro"
    video_model: str = "fal-ai/kling-video/v1.6/pro/image-to-video"

    VALID_ASPECT_RATIOS = ["1:1", "4:3", "3:4", "16:9", "9:16", "21:9", "9:21"]
    VALID_DURATIONS = ["5", "10"]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SettingsConfig":
        """Create from dictionary with validation."""
        settings = cls(
            aspect_ratio=str(data.get("aspect_ratio", "9:16")),
            transition_duration=str(data.get("transition_duration", "5")),
            image_model=str(data.get("image_model", cls.image_model)),
            video_model=str(data.get("video_model", cls.video_model)),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        """Validate settings values."""
        if self.aspect_ratio not in self.VALID_ASPECT_RATIOS:
            raise ConfigError(
                f"Invalid aspect_ratio '{self.aspect_ratio}'. "
                f"Valid options: {', '.join(self.VALID_ASPECT_RATIOS)}",
                field="settings.aspect_ratio",
            )

        if self.transition_duration not in self.VALID_DURATIONS:
            raise ConfigError(
                f"Invalid transition_duration '{self.transition_duration}'. "
                f"Valid options: {', '.join(self.VALID_DURATIONS)}",
                field="settings.transition_duration",
            )


@dataclass
class GlobalSceneConfig:
    """Global scene configuration."""

    location_prompt: str
    negative_prompt: str = "blurry, distorted, cartoon, low quality"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GlobalSceneConfig":
        """Create from dictionary with validation."""
        if "location_prompt" not in data:
            raise ConfigError(
                "Missing required field: global_scene.location_prompt",
                field="global_scene.location_prompt",
            )

        return cls(
            location_prompt=str(data["location_prompt"]),
            negative_prompt=str(data.get("negative_prompt", cls.negative_prompt)),
        )


@dataclass
class StarStitchConfig:
    """Complete StarStitch pipeline configuration."""

    project_name: str
    output_folder: str
    settings: SettingsConfig
    global_scene: GlobalSceneConfig
    sequence: List[SubjectConfig]
    _config_path: Optional[Path] = field(default=None, repr=False)
    _raw_data: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], config_path: Optional[Path] = None) -> "StarStitchConfig":
        """
        Create configuration from dictionary.
        
        Args:
            data: Dictionary containing configuration data.
            config_path: Optional path to the source config file.
            
        Returns:
            Validated StarStitchConfig instance.
            
        Raises:
            ConfigError: If configuration is invalid.
        """
        # Validate required top-level fields
        if "project_name" not in data:
            raise ConfigError("Missing required field: project_name", field="project_name")

        if "sequence" not in data or not data["sequence"]:
            raise ConfigError(
                "Missing or empty required field: sequence",
                field="sequence",
            )

        if len(data["sequence"]) < 2:
            raise ConfigError(
                "Sequence must contain at least 2 subjects (anchor + 1 target)",
                field="sequence",
            )

        if "global_scene" not in data:
            raise ConfigError(
                "Missing required field: global_scene",
                field="global_scene",
            )

        # Parse nested configurations
        settings = SettingsConfig.from_dict(data.get("settings", {}))
        global_scene = GlobalSceneConfig.from_dict(data["global_scene"])
        sequence = [
            SubjectConfig.from_dict(s, i) for i, s in enumerate(data["sequence"])
        ]

        return cls(
            project_name=str(data["project_name"]),
            output_folder=str(data.get("output_folder", "renders")),
            settings=settings,
            global_scene=global_scene,
            sequence=sequence,
            _config_path=config_path,
            _raw_data=data,
        )

    @classmethod
    def from_file(cls, config_path: Path) -> "StarStitchConfig":
        """
        Load configuration from a JSON file.
        
        Args:
            config_path: Path to the configuration file.
            
        Returns:
            Validated StarStitchConfig instance.
            
        Raises:
            ConfigError: If file cannot be read or parsed.
            FileNotFoundError: If config file doesn't exist.
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in config file: {e}")

        return cls.from_dict(data, config_path)

    @property
    def anchor(self) -> SubjectConfig:
        """Get the anchor (first) subject."""
        return self.sequence[0]

    @property
    def targets(self) -> List[SubjectConfig]:
        """Get all target subjects (excluding anchor)."""
        return self.sequence[1:]

    @property
    def config_hash(self) -> str:
        """
        Generate a hash of the configuration for state validation.
        
        This allows detecting if the config has changed between runs.
        """
        # Create a normalized string representation
        config_str = json.dumps(self._raw_data, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()[:12]

    def get_combined_prompt(self, visual_prompt: str) -> str:
        """
        Combine a visual prompt with the location prompt.
        
        Args:
            visual_prompt: The subject's visual description.
            
        Returns:
            Combined prompt string.
        """
        return f"{visual_prompt}, {self.global_scene.location_prompt}"

    def validate(self) -> List[str]:
        """
        Perform comprehensive validation of the configuration.
        
        Returns:
            List of warning messages (empty if no warnings).
            
        Raises:
            ConfigError: If critical validation errors are found.
        """
        warnings = []

        # Check for duplicate IDs
        ids = [s.id for s in self.sequence]
        if len(ids) != len(set(ids)):
            raise ConfigError(
                "Duplicate subject IDs found in sequence",
                field="sequence",
            )

        # Warn about very long prompts
        for i, subject in enumerate(self.sequence):
            combined = self.get_combined_prompt(subject.visual_prompt)
            if len(combined) > 500:
                warnings.append(
                    f"Subject '{subject.name}' has a very long combined prompt "
                    f"({len(combined)} chars). Consider shortening."
                )

        # Warn about short sequences
        if len(self.sequence) == 2:
            warnings.append(
                "Sequence has only 2 subjects. Consider adding more for a longer video."
            )

        return warnings

    def summary(self) -> str:
        """Get a human-readable summary of the configuration."""
        lines = [
            f"Project: {self.project_name}",
            f"Output: {self.output_folder}/",
            f"Aspect Ratio: {self.settings.aspect_ratio}",
            f"Transition Duration: {self.settings.transition_duration}s",
            f"Sequence: {len(self.sequence)} subjects",
            "  Subjects:",
        ]
        for i, subject in enumerate(self.sequence):
            prefix = "  → " if i == 0 else "    "
            lines.append(f"{prefix}{subject.name} ({subject.id})")

        return "\n".join(lines)


class ConfigLoader:
    """
    Configuration loader with logging and validation.
    
    Provides a high-level interface for loading and validating
    StarStitch configurations.
    """

    DEFAULT_CONFIG_PATH = Path("config.json")

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the config loader.
        
        Args:
            logger: Optional logger instance.
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def load(self, config_path: Optional[Path] = None) -> StarStitchConfig:
        """
        Load and validate configuration from file.
        
        Args:
            config_path: Path to config file. Uses default if None.
            
        Returns:
            Validated configuration instance.
            
        Raises:
            ConfigError: If configuration is invalid.
            FileNotFoundError: If config file doesn't exist.
        """
        path = config_path or self.DEFAULT_CONFIG_PATH
        self.logger.info(f"Loading configuration from: {path}")

        try:
            config = StarStitchConfig.from_file(path)

            # Run validation
            warnings = config.validate()
            for warning in warnings:
                self.logger.warning(warning)

            self.logger.info(f"Configuration loaded successfully")
            self.logger.debug(f"Config hash: {config.config_hash}")

            return config

        except ConfigError as e:
            self.logger.error(f"Configuration error: {e}")
            if e.field:
                self.logger.error(f"  Field: {e.field}")
            raise

        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {path}")
            raise

    def validate_only(self, config_path: Optional[Path] = None) -> bool:
        """
        Validate configuration without fully loading it.
        
        Args:
            config_path: Path to config file.
            
        Returns:
            True if valid, False otherwise.
        """
        try:
            self.load(config_path)
            self.logger.info("Configuration is valid!")
            return True
        except (ConfigError, FileNotFoundError) as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False
