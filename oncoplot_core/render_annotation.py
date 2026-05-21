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
    measure_label_height_in,
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
    annotations_position="bottom",
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
    # In annotation-only mode the "position" setting controls sample labels:
    # "top" → labels on top of the first track
    # "bottom" → labels below the last track
    _labels_on_top = _labels_visible and annotations_position == "top"
    _labels_on_bottom = _labels_visible and annotations_position == "bottom"
    # Reserve space sized to the actual rendered sample labels (uncapped), so
    # long IDs never overlap the tracks (top) or the legend (bottom).
    _label_h = (
        measure_label_height_in(samples, fontsize) if _labels_visible else 0.0
    )

    # Layout: header | (label spacer if top) | data rows | tracks
    _lbl_spacer_h = _label_h if _labels_on_top else 0
    height_ratios = (
        [header_h]
        + ([_lbl_spacer_h] if _labels_on_top else [])
        + [data_h] * n_data
        + [trk_h] * n_tracks
    )
    header_row = 0
    _lbl_spacer = 1 if _labels_on_top else None
    _off = int(_labels_on_top)
    data_start = 1 + _off
    trk_start = 1 + _off + n_data

    # ── Legend handles (built early so geometry can reserve room) ─
    legend_handles = build_categorical_legend_handles(
        clinical_cols, clinical_types, clinical_colors,
        clinical_data, track_options, display_names,
    )

    # ── Margin budget (inches) ──────────────────────────────────
    # Top reserves the title; bottom reserves the legend rows plus, when sample
    # labels sit under the plot, their measured height. Inches-based budgeting
    # keeps title->plot and plot->legend gaps stable across figure heights and
    # label lengths.
    n_legend_cols = min(5, len(legend_handles)) if legend_handles else 1
    n_legend_rows = (
        (len(legend_handles) + n_legend_cols - 1) // n_legend_cols
        if legend_handles
        else 0
    )
    legend_row_h = fontsize * 1.8 / 72
    legend_h = n_legend_rows * legend_row_h * 1.4
    legend_pad = 0.14 if legend_handles else 0.0

    title_h = (fontsize + 3) * 2.2 / 72 if title is not None else 0.0
    top_pad = title_h + 0.12

    _bottom_label_h = _label_h if _labels_on_bottom else 0.0
    bottom_pad = 0.10 + legend_pad + legend_h + _bottom_label_h

    content_h = sum(height_ratios)
    fig_height = content_h + top_pad + bottom_pad

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

    if _lbl_spacer is not None:
        fig.add_subplot(gs[_lbl_spacer, 0]).set_visible(False)
        fig.add_subplot(gs[_lbl_spacer, 1]).set_visible(False)

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
    _last_ax = all_axes[-1] if all_axes else None

    # ── Sample labels ─────────────────────────────────────────
    if _labels_on_top and _first_ax is not None:
        _first_ax.set_xticks(range(n_samples))
        _first_ax.tick_params(
            axis="x", top=True, labeltop=True,
            bottom=False, labelbottom=False,
        )
        _first_ax.set_xticklabels(
            samples, rotation=90, fontsize=max(fontsize - 2, 4), ha="left",
        )
    elif _labels_on_bottom and _last_ax is not None:
        _last_ax.set_xticks(range(n_samples))
        _last_ax.tick_params(
            axis="x", top=False, labeltop=False,
            bottom=True, labelbottom=True,
        )
        _last_ax.set_xticklabels(
            samples, rotation=90, fontsize=max(fontsize - 2, 4), ha="right",
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

    # ── Margins, legend & title (inches-based, see budget above) ──
    _bottom_lbl = _bottom_label_h / fig_height
    top_margin = 1.0 - top_pad / fig_height
    bottom = bottom_pad / fig_height

    _left, _right = 0.08, 0.95
    fig.subplots_adjust(
        left=_left, right=_right, top=top_margin, bottom=bottom,
    )

    # Center title & legend on the first track axes (actual position after layout)
    if _first_ax is not None:
        pos = _first_ax.get_position()
        _plot_center = (pos.x0 + pos.x1) / 2
    else:
        _plot_center = 0.5

    if legend_handles:
        fig.legend(
            handles=legend_handles,
            loc="upper center",
            ncol=n_legend_cols,
            fontsize=fontsize - 1,
            frameon=False,
            bbox_to_anchor=(
                _plot_center,
                bottom - _bottom_lbl - 0.4 * legend_pad / fig_height,
            ),
            handlelength=1.2,
            handleheight=1.0,
            columnspacing=1.0,
        )

    if title is not None:
        fig.suptitle(
            title, fontsize=fontsize + 3, fontweight="bold",
            x=_plot_center,
            y=top_margin + (0.06 + title_h) / fig_height,
            va="top",
        )
    return fig
