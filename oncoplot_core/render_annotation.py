"""Annotation-only renderer (no mutation matrix)."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from .render_shared import (
    render_data_rows,
    render_annotation_tracks,
    render_group_separators,
    build_categorical_legend_handles,
)


def draw_annotation_plot(
    samples,
    clinical_data=None,
    clinical_cols=None,
    clinical_types=None,
    clinical_colors=None,
    track_options=None,
    data_rows=None,
    data_row_cmaps=None,
    display_names=None,
    group_boundaries=None,
    show_sample_labels=False,
    title=None,
    fig_width=14,
    fontsize=8,
):
    """Render annotation-only plot (no mutation matrix)."""
    clinical_cols = clinical_cols or []
    clinical_types = clinical_types or {}
    clinical_colors = clinical_colors or {}
    data_rows = data_rows or {}
    data_row_cmaps = data_row_cmaps or {}
    display_names = display_names or {}
    track_options = track_options or {}
    group_boundaries = group_boundaries or {}

    n_samples = len(samples)
    n_tracks = len(clinical_cols)
    n_data = len(data_rows)

    # ── Figure geometry ─────────────────────────────────────────
    _n_grp_levels = len(group_boundaries)
    _grp_label_h = _n_grp_levels * fontsize * 2.5 / 72
    header_h = max(0.001, _grp_label_h)
    data_h = 0.6
    trk_h = 0.6

    _labels_visible = show_sample_labels and n_samples <= 80
    if _labels_visible:
        _max_lbl = max((len(str(s)) for s in samples), default=0)
        _label_h = min(2.5, _max_lbl * max(fontsize - 2, 4) * 0.5 / 72)
    else:
        _label_h = 0.0

    # Layout: header | data rows | tracks
    height_ratios = (
        [header_h]
        + [data_h] * n_data
        + [trk_h] * n_tracks
    )
    header_row = 0
    data_start = 1
    trk_start = 1 + n_data

    fig_height = sum(height_ratios) + 1.8
    if _labels_visible:
        fig_height += _label_h

    n_gs_rows = len(height_ratios)
    n_gs_cols = 2
    width_ratios = [max(n_samples * 0.25, 6), 3]

    fig = plt.figure(figsize=(fig_width, fig_height))
    gs = GridSpec(
        nrows=n_gs_rows,
        ncols=n_gs_cols,
        figure=fig,
        height_ratios=height_ratios,
        width_ratios=width_ratios,
        hspace=0.04,
        wspace=0.02,
    )

    all_axes = []

    # ── Header (invisible, reserves space for group labels) ─────
    fig.add_subplot(gs[header_row, 0]).set_visible(False)
    fig.add_subplot(gs[header_row, 1]).set_visible(False)

    # ── Data rows ───────────────────────────────────────────────
    render_data_rows(
        fig, gs, data_rows, data_row_cmaps, display_names,
        samples, data_start, n_samples, fontsize,
        all_axes,
    )

    _first_ax = all_axes[0] if all_axes else None

    # ── Annotation tracks ───────────────────────────────────────
    _n_before = len(all_axes)
    render_annotation_tracks(
        fig, gs, clinical_data, clinical_cols, clinical_types,
        clinical_colors, track_options, display_names,
        samples, trk_start, n_samples, fontsize,
        all_axes,
    )
    if _first_ax is None and len(all_axes) > _n_before:
        _first_ax = all_axes[_n_before]

    # ── Sample labels on first track ────────────────────────────
    if _labels_visible and _first_ax is not None:
        _first_ax.set_xticks(range(n_samples))
        _first_ax.tick_params(
            axis="x", top=True, labeltop=True,
            bottom=False, labelbottom=False,
        )
        _first_ax.set_xticklabels(
            samples, rotation=90, fontsize=max(fontsize - 2, 4), ha="left",
        )

    # ── Group separators & labels ───────────────────────────────
    if group_boundaries and _first_ax is not None:
        n_levels = len(group_boundaries)
        ylim = _first_ax.get_ylim()
        y_top = max(ylim)
        render_group_separators(
            group_boundaries, all_axes, _first_ax, y_top,
            n_levels, fontsize,
        )

    # ── Legend ───────────────────────────────────────────────────
    legend_handles = build_categorical_legend_handles(
        clinical_cols, clinical_types, clinical_colors,
        clinical_data, track_options, display_names,
    )

    n_legend_cols = min(5, len(legend_handles)) if legend_handles else 1
    n_legend_rows = (
        (len(legend_handles) + n_legend_cols - 1) // n_legend_cols
        if legend_handles else 0
    )
    row_frac = (fontsize * 1.8) / (fig_height * 72) if fig_height > 0 else 0
    legend_margin = n_legend_rows * row_frac * 1.4
    bottom = min(0.50, max(0.06, 0.02 + legend_margin))

    if legend_handles:
        fig.legend(
            handles=legend_handles,
            loc="upper center",
            ncol=n_legend_cols,
            fontsize=fontsize - 1,
            frameon=False,
            bbox_to_anchor=(0.45, bottom - 0.005),
            handlelength=1.2,
            handleheight=1.0,
            columnspacing=1.0,
        )

    if title is not None:
        fig.suptitle(
            title, fontsize=fontsize + 3, fontweight="bold", y=0.99,
        )
    fig.subplots_adjust(
        left=0.08, right=0.95, top=0.94, bottom=bottom,
    )
    return fig
