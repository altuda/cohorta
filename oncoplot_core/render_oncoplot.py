"""Full oncoplot renderer (matrix + TMB + gene frequency + tracks)."""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from matplotlib.colors import ListedColormap, BoundaryNorm

from .constants import BG_COLOR
from .render_shared import (
    render_data_rows,
    render_annotation_tracks,
    render_group_separators,
    build_categorical_legend_handles,
)


def draw_oncoplot(
    matrix,
    mutation_colors,
    clinical_data=None,
    clinical_cols=None,
    clinical_types=None,
    clinical_colors=None,
    data_rows=None,
    data_row_cmaps=None,
    display_names=None,
    track_options=None,
    group_boundaries=None,
    show_tmb=True,
    show_gene_freq=True,
    show_sample_labels=False,
    annotations_position="bottom",
    title=None,
    fig_width=14,
    fontsize=8,
):
    """Render the full oncoplot.

    *matrix* must already be sliced to top-N genes and column-sorted
    by the caller.
    """
    clinical_cols = clinical_cols or []
    clinical_types = clinical_types or {}
    clinical_colors = clinical_colors or {}
    data_rows = data_rows or {}
    data_row_cmaps = data_row_cmaps or {}
    display_names = display_names or {}
    track_options = track_options or {}
    group_boundaries = group_boundaries or {}

    genes = matrix.index.tolist()
    samples = matrix.columns.tolist()
    n_genes = len(genes)
    n_samples = len(samples)
    n_tracks = len(clinical_cols)
    n_data = len(data_rows)

    # ── Mutation type -> integer mapping ─────────────────────────
    all_mut_types = sorted(
        [t for t in matrix.stack().unique() if pd.notna(t)],
        key=lambda t: -(matrix == t).sum().sum(),
    )
    type_to_int = {t: i for i, t in enumerate(all_mut_types)}

    num_mat = np.full(matrix.shape, np.nan)
    for mt, idx in type_to_int.items():
        num_mat[matrix.values == mt] = idx

    colors_list = [mutation_colors.get(t, "#808080") for t in all_mut_types]
    cmap_mat = (
        ListedColormap(colors_list) if colors_list else ListedColormap(["#808080"])
    )
    cmap_mat.set_bad(color=BG_COLOR)

    if all_mut_types:
        bounds = np.arange(-0.5, len(all_mut_types) + 0.5, 1)
        norm_mat = BoundaryNorm(bounds, len(all_mut_types))
    else:
        norm_mat = None

    # ── Figure geometry ─────────────────────────────────────────
    _n_grp_levels = len(group_boundaries)
    _grp_label_h = _n_grp_levels * fontsize * 2.5 / 72
    tmb_h = (2.0 if show_tmb else 0.001) + _grp_label_h
    mat_h = max(n_genes * 0.45, 3.0)
    data_h = 0.6
    trk_h = 0.6
    gap_h = 0.25 if (n_data + n_tracks) > 0 else 0.0
    has_gap = gap_h > 0

    _labels_visible = show_sample_labels and n_samples <= 80
    _labels_on_top = _labels_visible and annotations_position == "bottom"
    _labels_on_bottom = _labels_visible and annotations_position == "top"
    if _labels_visible:
        _max_lbl = max((len(str(s)) for s in samples), default=0)
        _label_h = min(2.5, _max_lbl * max(fontsize - 2, 4) * 0.5 / 72)
    else:
        _label_h = 0.0

    if annotations_position == "top":
        height_ratios = (
            [tmb_h]
            + [trk_h] * n_tracks
            + [data_h] * n_data
            + ([gap_h] if has_gap else [])
            + [mat_h]
        )
        tmb_row = 0
        trk_start = 1
        data_start = 1 + n_tracks
        gap_row = 1 + n_tracks + n_data if has_gap else None
        mat_row = 1 + n_tracks + n_data + int(has_gap)
        _lbl_spacer = None
    else:
        _lbl_off = int(_labels_on_top)
        height_ratios = (
            [tmb_h]
            + ([_label_h] if _labels_on_top else [])
            + [mat_h]
            + ([gap_h] if has_gap else [])
            + [data_h] * n_data
            + [trk_h] * n_tracks
        )
        tmb_row = 0
        _lbl_spacer = 1 if _labels_on_top else None
        mat_row = 1 + _lbl_off
        gap_row = 2 + _lbl_off if has_gap else None
        data_start = 2 + _lbl_off + int(has_gap)
        trk_start = 2 + _lbl_off + int(has_gap) + n_data

    fig_height = sum(height_ratios) + 1.8
    if _labels_on_bottom:
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

    # ── 1. TMB stacked bar ─────────────────────────────────────
    ax_tmb = fig.add_subplot(gs[tmb_row, 0])
    all_axes.append(ax_tmb)
    if show_tmb:
        bottom_vals = np.zeros(n_samples)
        for mt in all_mut_types:
            counts = (matrix == mt).sum(axis=0).values.astype(float)
            ax_tmb.bar(
                np.arange(n_samples),
                counts,
                bottom=bottom_vals,
                color=mutation_colors.get(mt, "#808080"),
                width=1.0,
                linewidth=0,
            )
            bottom_vals += counts
        ax_tmb.set_xlim(-0.5, n_samples - 0.5)
        ax_tmb.set_ylabel("TMB", fontsize=fontsize)
        ax_tmb.tick_params(axis="x", bottom=False, labelbottom=False)
        ax_tmb.tick_params(axis="y", labelsize=fontsize - 1)
        ax_tmb.spines[["top", "right", "bottom"]].set_visible(False)
    else:
        ax_tmb.set_visible(False)

    fig.add_subplot(gs[tmb_row, 1]).set_visible(False)

    if _lbl_spacer is not None:
        fig.add_subplot(gs[_lbl_spacer, 0]).set_visible(False)
        fig.add_subplot(gs[_lbl_spacer, 1]).set_visible(False)

    # ── 2. Central matrix ──────────────────────────────────────
    ax_mat = fig.add_subplot(gs[mat_row, 0])
    all_axes.append(ax_mat)
    ax_mat.set_facecolor(BG_COLOR)
    if all_mut_types:
        _x_edges = np.arange(n_samples + 1) - 0.5
        _y_edges = np.arange(n_genes + 1) - 0.5
        _masked = np.ma.array(num_mat, mask=np.isnan(num_mat))
        ax_mat.pcolormesh(
            _x_edges, _y_edges, _masked,
            cmap=cmap_mat, norm=norm_mat,
            edgecolors="white", linewidth=0.5,
        )

    ax_mat.set_yticks(range(n_genes))
    ax_mat.set_yticklabels(genes, fontsize=fontsize, fontstyle="italic")
    ax_mat.tick_params(axis="y", length=0)
    ax_mat.set_xlim(-0.5, n_samples - 0.5)
    ax_mat.set_ylim(n_genes - 0.5, -0.5)

    if show_sample_labels and n_samples <= 80:
        ax_mat.set_xticks(range(n_samples))
        if annotations_position == "bottom":
            ax_mat.tick_params(
                axis="x", top=True, labeltop=True,
                bottom=False, labelbottom=False,
            )
            ax_mat.set_xticklabels(
                samples, rotation=90, fontsize=max(fontsize - 2, 4),
                ha="left",
            )
        else:
            ax_mat.set_xticklabels(
                samples, rotation=90, fontsize=max(fontsize - 2, 4),
            )
    else:
        ax_mat.set_xticks([])

    # ── 3. Gene-frequency bar ──────────────────────────────────
    if show_gene_freq:
        ax_freq = fig.add_subplot(gs[mat_row, 1], sharey=ax_mat)
        freq_pct = matrix.notna().sum(axis=1) / n_samples * 100
        bar_colors = []
        for g in genes:
            gene_vals = matrix.loc[g].dropna()
            if len(gene_vals) > 0:
                dominant = gene_vals.value_counts().index[0]
                bar_colors.append(mutation_colors.get(dominant, "#808080"))
            else:
                bar_colors.append("#808080")
        ax_freq.barh(
            np.arange(n_genes),
            freq_pct.values,
            color=bar_colors,
            height=0.75,
            linewidth=0,
        )
        ax_freq.set_xlabel("% Samples", fontsize=fontsize)
        ax_freq.tick_params(axis="y", left=False, labelleft=False)
        ax_freq.tick_params(axis="x", labelsize=fontsize - 1)
        ax_freq.spines[["top", "right", "left"]].set_visible(False)
        ax_freq.set_ylim(n_genes - 0.5, -0.5)
    else:
        fig.add_subplot(gs[mat_row, 1]).set_visible(False)

    # ── Spacer ─────────────────────────────────────────────────
    if gap_row is not None:
        fig.add_subplot(gs[gap_row, 0]).set_visible(False)
        fig.add_subplot(gs[gap_row, 1]).set_visible(False)

    # ── 4. Data rows ───────────────────────────────────────────
    render_data_rows(
        fig, gs, data_rows, data_row_cmaps, display_names,
        samples, data_start, n_samples, fontsize,
        all_axes, sharex_ax=ax_mat,
    )

    # ── 5. Annotation tracks ──────────────────────────────────
    render_annotation_tracks(
        fig, gs, clinical_data, clinical_cols, clinical_types,
        clinical_colors, track_options, display_names,
        samples, trk_start, n_samples, fontsize,
        all_axes, sharex_ax=ax_mat,
    )

    # ── 6. Group separators & labels ──────────────────────────
    if group_boundaries:
        n_levels = len(group_boundaries)
        label_ax = ax_tmb if show_tmb else ax_mat
        ylim = label_ax.get_ylim()
        y_top = max(ylim) if show_tmb else min(ylim)
        render_group_separators(
            group_boundaries, all_axes, label_ax, y_top,
            n_levels, fontsize,
        )

    # ── 7. Legend ──────────────────────────────────────────────
    legend_handles = [
        mpatches.Patch(color=mutation_colors.get(mt, "#808080"), label=mt)
        for mt in all_mut_types
    ]
    legend_handles.extend(
        build_categorical_legend_handles(
            clinical_cols, clinical_types, clinical_colors,
            clinical_data, track_options, display_names,
        )
    )

    n_legend_cols = min(5, len(legend_handles)) if legend_handles else 1
    n_legend_rows = (
        (len(legend_handles) + n_legend_cols - 1) // n_legend_cols
        if legend_handles
        else 0
    )
    row_frac = (fontsize * 1.8) / (fig_height * 72) if fig_height > 0 else 0
    legend_margin = n_legend_rows * row_frac * 1.4
    _bottom_lbl = (
        (_label_h / fig_height)
        if _labels_on_bottom and fig_height > 0
        else 0
    )
    bottom = min(0.50, max(0.06, 0.02 + legend_margin + _bottom_lbl))

    _left, _right = 0.08, 0.95
    top_margin = 0.94
    fig.subplots_adjust(
        left=_left, right=_right, top=top_margin, bottom=bottom,
    )

    # Center title & legend on the matrix axes (actual position after layout)
    pos = ax_mat.get_position()
    _plot_center = (pos.x0 + pos.x1) / 2

    if legend_handles:
        fig.legend(
            handles=legend_handles,
            loc="upper center",
            ncol=n_legend_cols,
            fontsize=fontsize - 1,
            frameon=False,
            bbox_to_anchor=(_plot_center, bottom - 0.005 - _bottom_lbl),
            handlelength=1.2,
            handleheight=1.0,
            columnspacing=1.0,
        )

    if title is not None:
        fig.suptitle(
            title, fontsize=fontsize + 3, fontweight="bold",
            x=_plot_center, y=0.99,
        )
    return fig
