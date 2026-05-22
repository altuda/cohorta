"""Utility helpers for colormaps and auto-detection."""

import colorsys

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import to_hex

from .constants import _SAMPLE_HINTS, _GENE_HINTS, _MUT_HINTS


def _get_cmap(name):
    """Return a matplotlib colormap by name (cross-version safe)."""
    try:
        return matplotlib.colormaps[name]
    except (AttributeError, KeyError):
        return plt.cm.get_cmap(name)


def _palette_colors(cmap, n):
    """Return *n* distinct colours derived from a colormap.

    For qualitative palettes (ListedColormap, e.g. tab10): when *n* fits within
    the palette its own colours are spread evenly; when *n* exceeds the palette
    size the palette colours are kept intact and the overflow is filled with
    evenly-spaced HSV hues, so every group gets a unique colour instead of the
    palette cycling and repeating. Continuous colormaps are sampled directly.
    """
    if hasattr(cmap, "colors"):
        k = len(cmap.colors)
        if n <= k:
            # Spread selections evenly across the palette for better variety
            indices = np.linspace(0, k - 1, n, dtype=int)
            return [to_hex(cmap.colors[idx]) for idx in indices]
        # More groups than palette colours: keep the palette, then extend with
        # evenly-spaced distinct hues for the overflow.
        base = [to_hex(c) for c in cmap.colors]
        n_extra = n - k
        extra = [
            to_hex(colorsys.hsv_to_rgb((j + 0.5) / n_extra, 0.65, 0.85))
            for j in range(n_extra)
        ]
        return base + extra
    return [to_hex(cmap(i / max(n - 1, 1))) for i in range(n)]


def _auto_assign_roles(columns):
    """Guess a role for every column; each singleton role is assigned
    at most once.  Returns ``{col_name: role_str}``."""
    roles = {}
    taken = set()
    for col in columns:
        lc = col.lower()
        role = "Skip"
        if "Sample ID" not in taken and any(p in lc for p in _SAMPLE_HINTS):
            role = "Sample ID"
        if role == "Skip" and "Gene / Feature" not in taken and any(
            p in lc for p in _GENE_HINTS
        ):
            role = "Gene / Feature"
        if role == "Skip" and "Mutation Type" not in taken and any(
            p in lc for p in _MUT_HINTS
        ):
            role = "Mutation Type"
        roles[col] = role
        if role != "Skip":
            taken.add(role)
    return roles
