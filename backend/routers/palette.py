"""Palette and color utility endpoints."""

from fastapi import APIRouter

from ..models import PaletteListResponse, PaletteColorsRequest, PaletteColorsResponse

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from oncoplot_core import (
    CONTINUOUS_CMAPS, CATEGORICAL_PALETTES,
    _get_cmap, _palette_colors,
)

router = APIRouter()


@router.get("/palettes", response_model=PaletteListResponse)
async def list_palettes():
    return PaletteListResponse(
        categorical=CATEGORICAL_PALETTES,
        continuous=CONTINUOUS_CMAPS,
    )


@router.post("/palette-colors", response_model=PaletteColorsResponse)
async def get_palette_colors(body: PaletteColorsRequest):
    cmap = _get_cmap(body.palette_name)
    colors = _palette_colors(cmap, body.n_colors)
    return PaletteColorsResponse(colors=colors)
