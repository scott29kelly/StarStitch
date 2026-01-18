"""
Template Loader
Manages pre-built scene templates for StarStitch.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class Template:
    """A StarStitch scene template."""
    name: str
    display_name: str
    description: str
    category: str  # viral, holidays, events, themes
    thumbnail: Optional[str] = None
    base_config: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    author: str = "StarStitch"
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "thumbnail": self.thumbnail,
            "base_config": self.base_config,
            "tags": self.tags,
            "author": self.author,
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Template":
        """Create from dictionary."""
        return cls(
            name=data.get("name", "unknown"),
            display_name=data.get("display_name", data.get("name", "Unknown")),
            description=data.get("description", ""),
            category=data.get("category", "themes"),
            thumbnail=data.get("thumbnail"),
            base_config=data.get("base_config", {}),
            tags=data.get("tags", []),
            author=data.get("author", "StarStitch"),
            version=data.get("version", "1.0")
        )
    
    @classmethod
    def from_file(cls, path: Path) -> "Template":
        """Load template from JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def apply_to_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply this template to a config, merging settings.
        
        The template provides defaults that can be overridden by the config.
        
        Args:
            config: User config to merge with template.
            
        Returns:
            Merged configuration.
        """
        # Start with template base config
        result = dict(self.base_config)
        
        # Merge top-level keys
        for key, value in config.items():
            if key == "settings" and "settings" in result:
                # Deep merge settings
                result["settings"] = {**result["settings"], **value}
            elif key == "global_scene" and "global_scene" in result:
                # Deep merge global_scene
                result["global_scene"] = {**result["global_scene"], **value}
            elif key == "audio" and "audio" in result:
                # Deep merge audio
                result["audio"] = {**result["audio"], **value}
            elif key == "sequence" and value:
                # User sequence replaces template sequence
                result["sequence"] = value
            else:
                result[key] = value
        
        return result


class TemplateLoader:
    """
    Loads and manages StarStitch templates.
    
    Template directory structure:
        templates/
        ├── index.json              # Template catalog
        ├── viral/
        │   ├── tiktok_morph.json
        │   └── reels_trend.json
        ├── holidays/
        │   ├── christmas.json
        │   └── halloween.json
        ├── events/
        │   └── birthday.json
        └── themes/
            ├── travel.json
            └── nature.json
    """
    
    CATEGORIES = ["viral", "holidays", "events", "themes"]
    
    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize the template loader.
        
        Args:
            templates_dir: Path to templates directory. Defaults to ./templates.
        """
        if templates_dir is None:
            # Default to templates/ in the project root
            templates_dir = Path(__file__).parent.parent / "templates"
        
        self.templates_dir = Path(templates_dir)
        self._templates: Dict[str, Template] = {}
        self._loaded = False
    
    def _ensure_loaded(self):
        """Ensure templates are loaded."""
        if not self._loaded:
            self.load_all()
    
    def load_all(self) -> Dict[str, Template]:
        """
        Load all templates from the templates directory.
        
        Returns:
            Dictionary of template name -> Template.
        """
        self._templates = {}
        
        if not self.templates_dir.exists():
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return self._templates
        
        # Load from index.json if it exists
        index_path = self.templates_dir / "index.json"
        if index_path.exists():
            try:
                with open(index_path) as f:
                    index = json.load(f)
                
                for template_data in index.get("templates", []):
                    template = Template.from_dict(template_data)
                    self._templates[template.name] = template
                    logger.debug(f"Loaded template from index: {template.name}")
                    
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load template index: {e}")
        
        # Also scan for individual template files
        for category in self.CATEGORIES:
            category_dir = self.templates_dir / category
            if category_dir.exists():
                for template_file in category_dir.glob("*.json"):
                    try:
                        template = Template.from_file(template_file)
                        # Override category from directory
                        template.category = category
                        self._templates[template.name] = template
                        logger.debug(f"Loaded template: {template.name} from {template_file}")
                    except (json.JSONDecodeError, IOError) as e:
                        logger.warning(f"Failed to load template {template_file}: {e}")
        
        # Load any root-level template files
        for template_file in self.templates_dir.glob("*.json"):
            if template_file.name != "index.json":
                try:
                    template = Template.from_file(template_file)
                    if template.name not in self._templates:
                        self._templates[template.name] = template
                        logger.debug(f"Loaded root template: {template.name}")
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Failed to load template {template_file}: {e}")
        
        self._loaded = True
        logger.info(f"Loaded {len(self._templates)} templates")
        
        return self._templates
    
    def get_template(self, name: str) -> Optional[Template]:
        """
        Get a template by name.
        
        Args:
            name: Template name.
            
        Returns:
            Template if found, None otherwise.
        """
        self._ensure_loaded()
        return self._templates.get(name)
    
    def list_templates(self, category: Optional[str] = None) -> List[Template]:
        """
        List all available templates, optionally filtered by category.
        
        Args:
            category: Optional category filter.
            
        Returns:
            List of templates.
        """
        self._ensure_loaded()
        
        templates = list(self._templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        return sorted(templates, key=lambda t: (t.category, t.display_name))
    
    def list_categories(self) -> List[Dict[str, Any]]:
        """
        List available categories with counts.
        
        Returns:
            List of category info dicts.
        """
        self._ensure_loaded()
        
        category_counts = {cat: 0 for cat in self.CATEGORIES}
        for template in self._templates.values():
            if template.category in category_counts:
                category_counts[template.category] += 1
        
        return [
            {"name": cat, "count": count}
            for cat, count in category_counts.items()
            if count > 0
        ]
    
    def search_templates(self, query: str) -> List[Template]:
        """
        Search templates by name, description, or tags.
        
        Args:
            query: Search query string.
            
        Returns:
            List of matching templates.
        """
        self._ensure_loaded()
        
        query_lower = query.lower()
        results = []
        
        for template in self._templates.values():
            # Search in name, display_name, description, and tags
            if (
                query_lower in template.name.lower() or
                query_lower in template.display_name.lower() or
                query_lower in template.description.lower() or
                any(query_lower in tag.lower() for tag in template.tags)
            ):
                results.append(template)
        
        return results
    
    def apply_template(
        self,
        template_name: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply a template to a config.
        
        Args:
            template_name: Name of the template to apply.
            config: User configuration to merge.
            
        Returns:
            Merged configuration.
            
        Raises:
            ValueError: If template not found.
        """
        template = self.get_template(template_name)
        
        if not template:
            available = ", ".join(self._templates.keys())
            raise ValueError(
                f"Template '{template_name}' not found. "
                f"Available templates: {available or 'none'}"
            )
        
        return template.apply_to_config(config)
    
    def create_config_from_template(
        self,
        template_name: str,
        project_name: str,
        sequence: Optional[List[Dict[str, str]]] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a complete config from a template.
        
        Args:
            template_name: Name of the template to use.
            project_name: Project name for the config.
            sequence: Optional sequence of subjects.
            overrides: Optional additional overrides.
            
        Returns:
            Complete configuration dictionary.
        """
        template = self.get_template(template_name)
        
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        config = {
            "project_name": project_name,
            **(overrides or {})
        }
        
        if sequence:
            config["sequence"] = sequence
        
        return template.apply_to_config(config)
    
    def save_template(self, template: Template):
        """
        Save a template to disk.
        
        Args:
            template: Template to save.
        """
        category_dir = self.templates_dir / template.category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        template_path = category_dir / f"{template.name}.json"
        
        with open(template_path, "w") as f:
            json.dump(template.to_dict(), f, indent=2)
        
        self._templates[template.name] = template
        logger.info(f"Saved template: {template.name} to {template_path}")
