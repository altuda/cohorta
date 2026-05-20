"""Utility helpers for colormaps and auto-detection."""

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
    """Extract *n* evenly-spaced colours from a colormap."""
    if hasattr(cmap, "colors"):
        k = len(cmap.colors)
        if n >= k:
            return [to_hex(cmap.colors[i % k]) for i in range(n)]
        # Spread selections evenly across the palette for better variety
        indices = np.linspace(0, k - 1, n, dtype=int)
        return [to_hex(cmap.colors[idx]) for idx in indices]
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
