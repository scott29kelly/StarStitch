"""
Template Routes
REST API endpoints for template management.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..models import (
    ErrorResponse,
    TemplateDetailResponse,
    TemplateInfo,
    TemplateListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Templates"])


def _get_template_loader():
    """Get the template loader instance."""
    from utils import TemplateLoader
    return TemplateLoader()


@router.get(
    "/templates",
    response_model=TemplateListResponse,
    summary="List available templates",
    description="Get all available scene templates with optional category filtering.",
)
async def list_templates(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    search: Optional[str] = Query(default=None, description="Search query"),
):
    """
    List all available templates.
    
    Templates can be filtered by category or searched by name/description/tags.
    """
    loader = _get_template_loader()
    
    # Get templates
    if search:
        templates = loader.search_templates(search)
        if category:
            templates = [t for t in templates if t.category == category]
    elif category:
        templates = loader.list_templates(category=category)
    else:
        templates = loader.list_templates()
    
    # Convert to response models
    template_infos = [
        TemplateInfo(
            name=t.name,
            display_name=t.display_name,
            description=t.description,
            category=t.category,
            tags=t.tags,
            thumbnail=t.thumbnail,
            author=t.author,
            version=t.version,
        )
        for t in templates
    ]
    
    # Get categories
    categories = loader.list_categories()
    
    return TemplateListResponse(
        templates=template_infos,
        categories=categories,
        total=len(template_infos),
    )


@router.get(
    "/templates/{template_name}",
    response_model=TemplateDetailResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Template not found"},
    },
    summary="Get template details",
    description="Get detailed information about a template including its base configuration.",
)
async def get_template(template_name: str):
    """
    Get detailed information about a specific template.
    
    Includes the full base configuration that will be applied when using the template.
    """
    loader = _get_template_loader()
    template = loader.get_template(template_name)
    
    if not template:
        available = [t.name for t in loader.list_templates()]
        raise HTTPException(
            status_code=404,
            detail=f"Template '{template_name}' not found. Available: {available}"
        )
    
    return TemplateDetailResponse(
        info=TemplateInfo(
            name=template.name,
            display_name=template.display_name,
            description=template.description,
            category=template.category,
            tags=template.tags,
            thumbnail=template.thumbnail,
            author=template.author,
            version=template.version,
        ),
        base_config=template.base_config,
    )


@router.get(
    "/templates/categories",
    response_model=list,
    summary="List template categories",
    description="Get a list of all template categories with counts.",
)
async def list_categories():
    """
    List all template categories.
    
    Returns category names and the number of templates in each.
    """
    loader = _get_template_loader()
    return loader.list_categories()
