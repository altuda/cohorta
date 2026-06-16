"""Full oncoplot renderer (matrix + TMB + gene frequency + tracks)."""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from matplotlib.colors import ListedColormap, BoundaryNorm

from .constants import BG_COLOR, TMB_HIGH_THRESHOLD
from .render_shared import (
    render_data_rows,
    render_annotation_tracks,
    render_group_separators,
    build_categorical_legend_handles,
    measure_label_height_in,
    annotation_track_heights,
    plan_group_header_levels,
)


def draw_oncoplot(
    matrix,
    mutation_colors,
    mutation_burden=None,
    panel_size_mb=None,
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

    # ── Legend handles (built early so geometry can reserve room) ─
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

    # ── Figure geometry ─────────────────────────────────────────
    _n_grp_levels = len(group_boundaries)
    # Group section labels are placed in a header band under the title (in
    # figure coords, after layout) rather than stacked on the TMB/matrix axis,
    # so they sit consistently regardless of TMB / annotation / label position.
    # Each level decides its own orientation/font/height so crowded (crumbled)
    # subgroups flip to vertical instead of overlapping — see
    # plan_group_header_levels. The band height is the sum of the per-level slots.
    _wr0_est = max(n_samples * 0.25, 6)
    _per_sample_in = (
        (fig_width * (0.95 - 0.08) * _wr0_est / (_wr0_est + 3)) / max(n_samples, 1)
    )
    _grp_plan = plan_group_header_levels(
        group_boundaries, _per_sample_in, fontsize
    )
    header_band_h = sum(p["height_in"] for p in _grp_plan.values())
    tmb_h = 2.0 if show_tmb else 0.001
    mat_h = max(n_genes * 0.45, 3.0)
    data_h = 0.6
    gap_h = 0.25

    _labels_visible = show_sample_labels and n_samples <= 80
    _labels_on_top = _labels_visible and annotations_position == "bottom"
    _labels_on_bottom = _labels_visible and annotations_position == "top"
    # Reserve space sized to the actual rendered sample labels (uncapped),
    # so long IDs never overlap the matrix/TMB (top) or the legend (bottom).
    _label_h = (
        measure_label_height_in(samples, fontsize) if _labels_visible else 0.0
    )

    # Each annotation track may pin itself "top"/"bottom" (relative to the
    # matrix); otherwise it follows the global annotations_position. Data rows
    # (rarely used) stay on the global side, adjacent to the matrix.
    def _eff_pos(c):
        p = (track_options.get(c) or {}).get("position")
        return p if p in ("top", "bottom") else annotations_position

    top_cols = [c for c in clinical_cols if _eff_pos(c) == "top"]
    bot_cols = [c for c in clinical_cols if _eff_pos(c) == "bottom"]
    top_heights = annotation_track_heights(top_cols, clinical_types, track_options)
    bot_heights = annotation_track_heights(bot_cols, clinical_types, track_options)
    data_on_top = annotations_position == "top"

    # Build the row plan top→bottom, tagging each row so the renderers address
    # rows by role instead of fragile offset arithmetic.
    height_ratios = []
    row_tags = []

    def _add_row(h, tag):
        height_ratios.append(h)
        row_tags.append(tag)

    _add_row(tmb_h, "tmb")
    for h in top_heights:
        _add_row(h, "top_trk")
    if data_on_top:
        for _ in range(n_data):
            _add_row(data_h, "data")
    if top_cols or (data_on_top and n_data):
        _add_row(gap_h, "gap")
    if _labels_on_top:
        _add_row(_label_h, "lblspacer")
    _add_row(mat_h, "matrix")
    if bot_cols or (not data_on_top and n_data):
        _add_row(gap_h, "gap")
    if not data_on_top:
        for _ in range(n_data):
            _add_row(data_h, "data")
    for h in bot_heights:
        _add_row(h, "bot_trk")

    tmb_row = 0
    mat_row = row_tags.index("matrix")
    _lbl_spacer = row_tags.index("lblspacer") if "lblspacer" in row_tags else None
    top_trk_start = row_tags.index("top_trk") if "top_trk" in row_tags else None
    bot_trk_start = row_tags.index("bot_trk") if "bot_trk" in row_tags else None
    data_start = row_tags.index("data") if "data" in row_tags else 0
    gap_rows = [i for i, t in enumerate(row_tags) if t == "gap"]

    # ── Margin budget (inches) ──────────────────────────────────
    # Top reserves the title; bottom reserves the legend rows plus, when the
    # sample labels sit under the plot, their measured height. Computing these
    # in inches (instead of fixed fractions) keeps the title->plot and
    # plot->legend gaps constant regardless of figure height or label length.
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
    top_pad = title_h + 0.12 + header_band_h

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

    # ── 1. Per-sample mutation-burden stacked bar ──────────────
    # Counts every non-synonymous variant in each sample across ALL genes (via
    # mutation_burden), not just the displayed top-N — that is the real
    # per-sample mutation load. Falls back to the displayed-matrix count only if
    # no burden is supplied. When panel_size_mb is given the counts are divided
    # by it to show true TMB in mut/Mb, with the FDA TMB-high line at 10.
    _is_tmb = panel_size_mb is not None and panel_size_mb > 0
    _scale = (1.0 / panel_size_mb) if _is_tmb else 1.0
    ax_tmb = fig.add_subplot(gs[tmb_row, 0])
    all_axes.append(ax_tmb)
    if show_tmb:
        bottom_vals = np.zeros(n_samples)
        x = np.arange(n_samples)
        if mutation_burden is not None:
            burden = mutation_burden.reindex(index=samples, fill_value=0)
            # Stack legend types first (consistent colour order), then any
            # burden-only classes so the totals stay exact.
            stack_order = [c for c in all_mut_types if c in burden.columns]
            stack_order += [c for c in burden.columns if c not in set(all_mut_types)]
            for mt in stack_order:
                counts = burden[mt].values.astype(float) * _scale
                ax_tmb.bar(
                    x, counts, bottom=bottom_vals,
                    color=mutation_colors.get(mt, "#808080"),
                    width=1.0, linewidth=0,
                )
                bottom_vals += counts
        else:
            for mt in all_mut_types:
                counts = (matrix == mt).sum(axis=0).values.astype(float) * _scale
                ax_tmb.bar(
                    x, counts, bottom=bottom_vals,
                    color=mutation_colors.get(mt, "#808080"),
                    width=1.0, linewidth=0,
                )
                bottom_vals += counts
        ax_tmb.set_xlim(-0.5, n_samples - 0.5)
        if _is_tmb:
            ax_tmb.set_ylabel("TMB (mut/Mb)", fontsize=fontsize)
            # FDA TMB-high cut-point (KEYNOTE-158); only label it if in range.
            if bottom_vals.max() >= TMB_HIGH_THRESHOLD * 0.5:
                ax_tmb.axhline(
                    TMB_HIGH_THRESHOLD, color="#444444",
                    linestyle="--", linewidth=0.8,
                )
                ax_tmb.text(
                    n_samples - 0.5, TMB_HIGH_THRESHOLD,
                    f" TMB-high ≥{TMB_HIGH_THRESHOLD:g}",
                    va="bottom", ha="right",
                    fontsize=max(fontsize - 2, 5), color="#444444",
                )
        else:
            ax_tmb.set_ylabel("Mutations", fontsize=fontsize)
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
        # Stacked horizontal bar: each gene's bar is broken down by mutation
        # type (colours match the heatmap), so the segments show the alteration
        # composition rather than a single "dominant type" colour. The total
        # length still equals the % of samples carrying any alteration, since
        # every mutated cell holds exactly one type.
        y = np.arange(n_genes)
        left_vals = np.zeros(n_genes)
        for mt in all_mut_types:
            pct = (matrix == mt).sum(axis=1).values.astype(float) / n_samples * 100
            ax_freq.barh(
                y, pct, left=left_vals,
                color=mutation_colors.get(mt, "#808080"),
                height=0.75, linewidth=0,
            )
            left_vals += pct
        ax_freq.set_xlabel("% Samples", fontsize=fontsize)
        ax_freq.tick_params(axis="y", left=False, labelleft=False)
        ax_freq.tick_params(axis="x", labelsize=fontsize - 1)
        ax_freq.spines[["top", "right", "left"]].set_visible(False)
        ax_freq.set_ylim(n_genes - 0.5, -0.5)
    else:
        fig.add_subplot(gs[mat_row, 1]).set_visible(False)

    # ── Spacers (gaps between matrix and the track blocks) ─────
    for _g in gap_rows:
        fig.add_subplot(gs[_g, 0]).set_visible(False)
        fig.add_subplot(gs[_g, 1]).set_visible(False)

    # ── 4. Data rows ───────────────────────────────────────────
    render_data_rows(
        fig, gs, data_rows, data_row_cmaps, display_names,
        samples, data_start, n_samples, fontsize,
        all_axes, sharex_ax=ax_mat,
    )

    # ── 5. Annotation tracks (split into top / bottom blocks) ──
    if top_cols and top_trk_start is not None:
        render_annotation_tracks(
            fig, gs, clinical_data, top_cols, clinical_types,
            clinical_colors, track_options, display_names,
            samples, top_trk_start, n_samples, fontsize,
            all_axes, sharex_ax=ax_mat,
        )
    if bot_cols and bot_trk_start is not None:
        render_annotation_tracks(
            fig, gs, clinical_data, bot_cols, clinical_types,
            clinical_colors, track_options, display_names,
            samples, bot_trk_start, n_samples, fontsize,
            all_axes, sharex_ax=ax_mat,
        )

    # ── 6. Group separator lines (labels drawn in header band below) ──
    if group_boundaries:
        n_levels = len(group_boundaries)
        render_group_separators(
            group_boundaries, all_axes, None, 0,
            n_levels, fontsize, draw_labels=False,
        )

    # ── 7. Margins, legend & title (inches-based, see budget above) ──
    _bottom_lbl = _bottom_label_h / fig_height
    top_margin = 1.0 - top_pad / fig_height
    bottom = bottom_pad / fig_height

    _left, _right = 0.08, 0.95
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
            bbox_to_anchor=(
                _plot_center,
                bottom - _bottom_lbl - 0.4 * legend_pad / fig_height,
            ),
            handlelength=1.2,
            handleheight=1.0,
            columnspacing=1.0,
        )

    # Group section labels: a header band between the title and the content.
    # x is taken from the matrix axis (after layout) so labels centre over the
    # right columns; y is stacked by level with the outermost level on top.
    if group_boundaries and _n_grp_levels and _grp_plan:
        _inv = fig.transFigure.inverted()
        _band_top_in = header_band_h  # measured from top_margin upward
        # Stack levels from the top of the band down: outermost level (0) on top.
        _cursor_in = _band_top_in
        for lvl in sorted(group_boundaries):
            _p = _grp_plan[lvl]
            _h_in = _p["height_in"]
            _center_in = _cursor_in - _h_in / 2.0
            _cursor_in -= _h_in
            _y = top_margin + _center_in / fig_height
            _vertical = _p["orient"] == "v"
            for (lbl, start, end) in group_boundaries[lvl]:
                _cx = (start + end - 1) / 2.0
                _fx = _inv.transform(ax_mat.transData.transform((_cx, 0)))[0]
                fig.text(
                    _fx, _y, lbl,
                    ha="center", va="center",
                    rotation=90 if _vertical else 0,
                    fontsize=_p["font"],
                    fontweight="bold" if lvl == 0 else "semibold",
                )

    if title is not None:
        fig.suptitle(
            title, fontsize=fontsize + 3, fontweight="bold",
            x=_plot_center,
            y=top_margin + (0.06 + title_h + header_band_h) / fig_height,
            va="top",
        )
    return fig
