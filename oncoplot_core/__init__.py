"""oncoplot_core — plotting and data logic for the Oncoplot Builder."""

from .constants import (
    COLUMN_ROLES, DEFAULT_MUT_COLORS, FALLBACK_COLORS, BG_COLOR,
    CONTINUOUS_CMAPS, CATEGORICAL_PALETTES,
)
from .helpers import _get_cmap, _palette_colors, _auto_assign_roles
from .data import build_mutation_matrix, sort_samples
from .render_oncoplot import draw_oncoplot
from .render_annotation import draw_annotation_plot
