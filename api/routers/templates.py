"""
Templates Router
REST endpoints for managing templates.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

# Import the template loader from utils
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.template_loader import TemplateLoader, Template

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["templates"])

# Template loader instance
_template_loader: Optional[TemplateLoader] = None


def get_template_loader() -> TemplateLoader:
    """Get or create the template loader instance."""
    global _template_loader
    if _template_loader is None:
        _template_loader = TemplateLoader()
    return _template_loader


class TemplateResponse(BaseModel):
    """Response model for a template."""
    name: str
    display_name: str
    description: str
    category: str
    thumbnail: Optional[str] = None
    tags: List[str] = []
    author: str = "StarStitch"
    version: str = "1.0"
    base_config: Dict[str, Any] = {}


class TemplateListResponse(BaseModel):
    """Response model for template list."""
    templates: List[TemplateResponse]
    total: int
    categories: List[Dict[str, Any]] = []


class CategoryResponse(BaseModel):
    """Response model for a category."""
    name: str
    count: int


def template_to_response(template: Template) -> TemplateResponse:
    """Convert a Template to TemplateResponse."""
    return TemplateResponse(
        name=template.name,
        display_name=template.display_name,
        description=template.description,
        category=template.category,
        thumbnail=template.thumbnail,
        tags=template.tags,
        author=template.author,
        version=template.version,
        base_config=template.base_config,
    )


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    category: Optional[str] = None,
    search: Optional[str] = None,
):
    """
    List all available templates.

    Optionally filter by category or search query.
    """
    loader = get_template_loader()

    if search:
        templates = loader.search_templates(search)
        if category:
            templates = [t for t in templates if t.category == category]
    else:
        templates = loader.list_templates(category=category)

    categories = loader.list_categories()

    return TemplateListResponse(
        templates=[template_to_response(t) for t in templates],
        total=len(templates),
        categories=categories,
    )


@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories():
    """
    List all template categories with counts.
    """
    loader = get_template_loader()
    categories = loader.list_categories()

    return [CategoryResponse(name=c["name"], count=c["count"]) for c in categories]


@router.get("/{template_name}", response_model=TemplateResponse)
async def get_template(template_name: str):
    """
    Get a specific template by name.
    """
    loader = get_template_loader()
    template = loader.get_template(template_name)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found",
        )

    return template_to_response(template)


@router.post("/{template_name}/apply", response_model=Dict[str, Any])
async def apply_template(
    template_name: str,
    config: Dict[str, Any] = {},
):
    """
    Apply a template to a configuration.

    Returns the merged configuration with template defaults.
    """
    loader = get_template_loader()

    try:
        merged = loader.apply_template(template_name, config)
        return merged
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
