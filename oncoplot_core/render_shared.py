"""Shared rendering helpers used by both draw_oncoplot and draw_annotation_plot."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap, BoundaryNorm, Normalize
from matplotlib.cm import ScalarMappable

from .constants import FALLBACK_COLORS
from .helpers import _get_cmap


# Numeric tracks can be drawn as an x/y chart instead of a colour strip.
VALUE_PLOT_STYLES = ("columns", "points", "lollipop", "connected")
_TRACK_TILE_H = 0.6   # height (inches) of a colour-strip track row
_TRACK_PLOT_H = 1.3   # height (inches) of a value-chart track row


def _fmt_num(v):
    """Compact numeric label: integers without a decimal, else one decimal."""
    if v is None:
        return ""
    f = float(v)
    if np.isnan(f):
        return ""
    return str(int(f)) if f == int(f) else f"{f:.1f}"


def annotation_track_heights(clinical_cols, clinical_types, track_options):
    """Per-track row heights (inches).

    Value-chart tracks (numeric columns set to columns/points/lollipop/
    connected) get a taller row than plain colour strips so the curve is
    legible. Returns one height per column, in *clinical_cols* order.
    """
    clinical_cols = clinical_cols or []
    clinical_types = clinical_types or {}
    track_options = track_options or {}
    heights = []
    for col in clinical_cols:
        opts = track_options.get(col, {})
        is_cont = clinical_types.get(col, "Categorical") == "Continuous"
        if is_cont and opts.get("value_plot") in VALUE_PLOT_STYLES:
            heights.append(_TRACK_PLOT_H)
        else:
            heights.append(_TRACK_TILE_H)
    return heights


def _style_value_track(ax, label, n_samples, fontsize, vmin, vmax):
    """Style a numeric value-chart track axis (name + min/max scale, no grid)."""
    ax.set_xlim(-0.5, n_samples - 0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_visible(True)
        ax.spines[s].set_linewidth(0.4)
        ax.spines[s].set_color("#999999")
    ticks = sorted({round(vmin, 4), round(vmax, 4)})
    ax.set_yticks(ticks)
    ax.set_yticklabels([_fmt_num(t) for t in ticks], fontsize=max(fontsize - 2, 4))
    ax.tick_params(axis="x", bottom=False, labelbottom=False)
    ax.tick_params(axis="y", length=2)
    ax.set_ylabel(
        label, fontsize=fontsize, fontweight="semibold",
        rotation=0, ha="right", va="center", labelpad=8,
    )


def measure_text_width_in(texts, fontsize, dpi=100, fontweight="normal"):
    """Rendered width (inches) of each string at *fontsize*, keyed by str(text).

    Measures real bounding boxes on a throwaway figure (like
    :func:`measure_label_height_in`) so fitting reflects actual proportional-font
    widths rather than character-count guesses. *fontweight* must match how the
    text is actually drawn — semibold/bold are wider than normal, and measuring
    the wrong weight under-reserves space (clipping long labels).
    """
    out = {}
    if not texts:
        return out
    fig_tmp = plt.figure(figsize=(1, 1), dpi=dpi)
    try:
        renderer = fig_tmp.canvas.get_renderer()
        for t in texts:
            txt = fig_tmp.text(0, 0, str(t), fontsize=fontsize, fontweight=fontweight)
            bb = txt.get_window_extent(renderer)
            txt.remove()
            out[str(t)] = bb.width / dpi
    finally:
        plt.close(fig_tmp)
    return out


def compute_left_margin_frac(
    labels, fig_width, fontsize, has_value_chart=False,
    pad_in=0.16, floor=0.08, cap=0.45,
):
    """Left-margin fraction wide enough for the longest left-side row label.

    Gene names and track titles are drawn to the left of the plot; a fixed
    margin clips long ones (e.g. "Material Description"). This measures the
    widest label and returns a figure-fraction margin sized to fit it (with a
    pad), clamped to a sane range. *has_value_chart* adds room for the numeric
    y-ticks that value-chart tracks place left of their title.
    """
    # Track titles render semibold (wider than normal) — measure that weight so
    # the reserved margin actually fits them.
    widths = measure_text_width_in(
        [str(x) for x in labels], fontsize, fontweight="semibold"
    )
    max_in = max(widths.values()) if widths else 0.0
    tick_allow = 0.0
    if has_value_chart:
        _tn = measure_text_width_in(["0000"], max(fontsize - 2, 4))
        tick_allow = _tn.get("0000", 0.0) + 8.0 / 72  # 8 pt labelpad
    left_in = max_in + tick_allow + pad_in
    return min(cap, max(floor, left_in / max(fig_width, 1e-6)))


def plan_group_header_levels(
    group_boundaries, per_sample_in, fontsize, pad_in=0.06,
):
    """Decide per-level orientation/font/height for the group-header band.

    Returns ``{level: {"orient": "h"|"v", "font": float, "height_in": float}}``.
    For each grouping level the labels are kept horizontal if they fit their
    blocks (optionally shrunk to a 5 pt floor); when even that overflows — the
    "crumbled subgroup" case — the level flips to vertical so neighbours can no
    longer overlap, and the band height grows to hold the longest label.
    """
    plan = {}
    if not group_boundaries:
        return plan
    _font_floor = 5.0
    for lvl in sorted(group_boundaries):
        base_f = float(max(fontsize - min(lvl, 2), 5))
        blocks = group_boundaries[lvl]
        # Level 0 renders bold, deeper levels semibold — measure that weight.
        _weight = "bold" if lvl == 0 else "semibold"
        widths = measure_text_width_in(
            [lbl for lbl, _, _ in blocks], base_f, fontweight=_weight
        )

        fits = True
        min_block_in = float("inf")
        max_lbl_in = 0.0
        f_fit = base_f
        for lbl, start, end in blocks:
            bw = max((end - start), 1) * per_sample_in
            lw = widths.get(str(lbl), 0.0)
            min_block_in = min(min_block_in, bw)
            max_lbl_in = max(max_lbl_in, lw)
            if lw > bw * 0.95:
                fits = False
            if lw > 0:
                f_fit = min(f_fit, base_f * (bw * 0.95) / lw)

        if fits:
            plan[lvl] = {
                "orient": "h", "font": base_f,
                "height_in": base_f * 1.6 / 72 + pad_in,
            }
        elif f_fit >= _font_floor:
            plan[lvl] = {
                "orient": "h", "font": f_fit,
                "height_in": f_fit * 1.6 / 72 + pad_in,
            }
        else:
            # Vertical: pick a font whose (rotated) horizontal footprint still
            # fits the narrowest block, so vertical labels don't overlap either.
            vfont = min(base_f, max(min_block_in * 72 / 1.4, 4.0))
            vfont = max(vfont, 4.0)
            band_in = max_lbl_in * (vfont / base_f) + 2 * pad_in
            plan[lvl] = {"orient": "v", "font": vfont, "height_in": band_in}
    return plan


def measure_label_height_in(samples, fontsize, rotation=90, pad_in=0.08, dpi=100):
    """Vertical extent (inches) the sample labels need when rotated.

    Rather than estimating from character counts, this renders each label on a
    throwaway figure and measures its real bounding box, so the reserved space
    matches the actual text (proportional fonts, wide glyphs, etc.) and there is
    no arbitrary cap. The result feeds the spacer row / bottom margin that keeps
    long sample IDs from overlapping the matrix, tracks, or legend.
    """
    if not samples:
        return 0.0
    label_fs = max(fontsize - 2, 4)
    fig_tmp = plt.figure(figsize=(1, 1), dpi=dpi)
    try:
        renderer = fig_tmp.canvas.get_renderer()
        max_px = 0.0
        for s in samples:
            txt = fig_tmp.text(0, 0, str(s), fontsize=label_fs, rotation=rotation)
            bb = txt.get_window_extent(renderer)
            txt.remove()
            if bb.height > max_px:
                max_px = bb.height
    finally:
        plt.close(fig_tmp)
    return max_px / dpi + pad_in


def style_track(ax, label, n_samples, fontsize):
    """Apply consistent styling to a data-row or annotation-track axis."""
    for j in range(n_samples + 1):
        ax.axvline(j - 0.5, color="white", linewidth=0.3)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.4)
        spine.set_color("#999999")
    ax.set_yticks([0])
    ax.set_yticklabels([label], fontsize=fontsize, fontweight="semibold")
    ax.tick_params(axis="x", bottom=False, labelbottom=False)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(-0.5, n_samples - 0.5)


def render_data_rows(
    fig, gs, data_rows, data_row_cmaps, display_names,
    samples, data_start, n_samples, fontsize,
    all_axes, sharex_ax=None,
):
    """Render continuous data-row heatmaps into the grid."""
    if not data_rows:
        return
    for dr_idx, (dr_col, dr_values) in enumerate(data_rows.items()):
        row_idx = data_start + dr_idx
        kw = {"sharex": sharex_ax} if sharex_ax else {}
        ax_dr = fig.add_subplot(gs[row_idx, 0], **kw)
        vals = dr_values.reindex(samples).values.astype(float)
        cm_name = data_row_cmaps.get(dr_col, "viridis")
        dr_cmap = _get_cmap(cm_name).copy()
        dr_cmap.set_bad(color="#F0F0F0")
        _dr_masked = np.ma.array(vals, mask=np.isnan(vals)).reshape(1, -1)
        _dr_x = np.arange(n_samples + 1) - 0.5
        _dr_y = np.array([-0.5, 0.5])
        ax_dr.pcolormesh(
            _dr_x, _dr_y, _dr_masked,
            cmap=dr_cmap, edgecolors="white", linewidth=0.3,
        )
        ax_dr.set_ylim(-0.5, 0.5)
        label = display_names.get(dr_col, dr_col)
        style_track(ax_dr, label, n_samples, fontsize)
        all_axes.append(ax_dr)

        ax_cb = fig.add_subplot(gs[row_idx, 1])
        ax_cb.set_axis_off()
        valid = vals[~np.isnan(vals)]
        if len(valid) > 0:
            _dr_sm = ScalarMappable(
                cmap=dr_cmap,
                norm=Normalize(vmin=np.nanmin(vals), vmax=np.nanmax(vals)),
            )
            cb = fig.colorbar(
                _dr_sm, ax=ax_cb, fraction=0.9, aspect=8,
                pad=0.05, location="left",
            )
            cb.ax.tick_params(labelsize=fontsize - 1)


def render_annotation_tracks(
    fig, gs, clinical_data, clinical_cols, clinical_types,
    clinical_colors, track_options, display_names,
    samples, trk_start, n_samples, fontsize,
    all_axes, sharex_ax=None,
):
    """Render categorical/continuous annotation tracks into the grid."""
    if not clinical_cols or clinical_data is None:
        return
    for t_idx, col in enumerate(clinical_cols):
        row_idx = trk_start + t_idx
        kw = {"sharex": sharex_ax} if sharex_ax else {}
        ax_trk = fig.add_subplot(gs[row_idx, 0], **kw)
        values = clinical_data.reindex(samples)[col]
        var_type = clinical_types.get(col, "Categorical")
        _opts = track_options.get(col, {})
        _tile_color = _opts.get("tile_color")
        _value_plot = _opts.get("value_plot")

        # ── Numeric value chart (columns / points / lollipop / line) ──
        if var_type == "Continuous" and _value_plot in VALUE_PLOT_STYLES:
            num_vals = pd.to_numeric(values, errors="coerce").values.astype(float)
            x = np.arange(n_samples)
            color = _opts.get("plot_color") or "#4C72B0"
            size = float(_opts.get("plot_size") or 1.0)
            finite = num_vals[np.isfinite(num_vals)]
            vmin = float(finite.min()) if finite.size else 0.0
            vmax = float(finite.max()) if finite.size else 1.0
            # Bars/lollipops grow from zero when the data spans zero, otherwise
            # from the data minimum so a tight positive range isn't flattened
            # against a far-away zero baseline.
            base = 0.0 if vmin <= 0 <= vmax else vmin

            if _value_plot == "columns":
                heights = np.where(np.isfinite(num_vals), num_vals - base, 0.0)
                ax_trk.bar(
                    x, heights, bottom=base,
                    width=max(0.05, min(1.0, 0.8 * size)),
                    color=color, linewidth=0,
                )
            elif _value_plot == "points":
                ax_trk.scatter(x, num_vals, s=36 * size, color=color, zorder=3)
            elif _value_plot == "lollipop":
                ax_trk.vlines(
                    x, base, num_vals, color=color,
                    linewidth=max(0.5, 1.0 * size), zorder=2,
                )
                ax_trk.scatter(x, num_vals, s=36 * size, color=color, zorder=3)
            else:  # connected
                _m = np.isfinite(num_vals)
                ax_trk.plot(
                    x[_m], num_vals[_m], color=color,
                    linewidth=1.2 * size,
                    marker="o", markersize=5 * size, zorder=3,
                )

            span = (vmax - vmin) or (abs(vmax) or 1.0)
            pad = span * 0.15
            lo = min(vmin, base) - pad
            hi = max(vmax, base) + pad
            ax_trk.set_ylim(lo, hi)
            if _value_plot in ("columns", "lollipop") and lo < base < hi:
                ax_trk.axhline(base, color="#cccccc", linewidth=0.5, zorder=1)

            label = display_names.get(col, col)
            _style_value_track(ax_trk, label, n_samples, fontsize, vmin, vmax)
            all_axes.append(ax_trk)
            fig.add_subplot(gs[row_idx, 1]).set_visible(False)
            continue

        if var_type == "Categorical":
            unique_vals = sorted(values.dropna().unique(), key=str)
            val_to_int = {v: i for i, v in enumerate(unique_vals)}
            numeric_row = np.array(
                [
                    val_to_int[v]
                    if pd.notna(v) and v in val_to_int
                    else np.nan
                    for v in values
                ]
            ).reshape(1, -1)
            col_map = clinical_colors.get(col, {})
            if _tile_color:
                tc_list = [_tile_color] * max(len(unique_vals), 1)
            else:
                # Color-map keys arrive from the frontend as strings (the
                # unique values are sent JSON-encoded via .astype(str)), so look
                # up by str(v) — otherwise numeric columns (e.g. Age) never match
                # and silently fall back to the default palette.
                tc_list = [
                    col_map.get(
                        str(v), FALLBACK_COLORS[i % len(FALLBACK_COLORS)]
                    )
                    for i, v in enumerate(unique_vals)
                ]
            tcmap = ListedColormap(tc_list)
            tcmap.set_bad(color="#F0F0F0")
            tb = np.arange(-0.5, len(unique_vals) + 0.5, 1)
            tnorm = BoundaryNorm(tb, len(unique_vals))
            _tc_masked = np.ma.array(numeric_row, mask=np.isnan(numeric_row))
            _tc_x = np.arange(n_samples + 1) - 0.5
            _tc_y = np.array([-0.5, 0.5])
            ax_trk.pcolormesh(
                _tc_x, _tc_y, _tc_masked,
                cmap=tcmap, norm=tnorm,
                edgecolors="white", linewidth=0.3,
            )
            ax_trk.set_ylim(-0.5, 0.5)
            num_vals = None
            trk_cmap = None
        else:
            num_vals = (
                pd.to_numeric(values, errors="coerce")
                .values.astype(float)
            )
            _ct_x = np.arange(n_samples + 1) - 0.5
            _ct_y = np.array([-0.5, 0.5])
            trk_cmap = None
            if _tile_color:
                _flat_cmap = ListedColormap([_tile_color])
                _flat_cmap.set_bad(color="#F0F0F0")
                _ct_flat = np.ma.array(
                    np.zeros(len(num_vals)),
                    mask=np.isnan(num_vals),
                ).reshape(1, -1)
                ax_trk.pcolormesh(
                    _ct_x, _ct_y, _ct_flat,
                    cmap=_flat_cmap, vmin=-0.5, vmax=0.5,
                    edgecolors="white", linewidth=0.3,
                )
            else:
                cm_name = clinical_colors.get(col, "viridis")
                # A column may carry a leftover categorical colour *map* (dict)
                # from before it was switched to Continuous; fall back to a real
                # colormap name in that case rather than crashing.
                if not isinstance(cm_name, str):
                    cm_name = "viridis"
                trk_cmap = _get_cmap(cm_name).copy()
                trk_cmap.set_bad(color="#F0F0F0")
                _ct_masked = np.ma.array(
                    num_vals, mask=np.isnan(num_vals),
                ).reshape(1, -1)
                ax_trk.pcolormesh(
                    _ct_x, _ct_y, _ct_masked,
                    cmap=trk_cmap, edgecolors="white", linewidth=0.3,
                )
            ax_trk.set_ylim(-0.5, 0.5)

        # Show values as text centred in each tile
        if _opts.get("show_values"):
            _txt_color = _opts.get("text_color", "#000000")
            for j, v in enumerate(values):
                if pd.notna(v):
                    if isinstance(v, (int, float, np.integer, np.floating)):
                        _txt = (
                            str(int(v))
                            if float(v) == int(float(v))
                            else f"{v:.1f}"
                        )
                    else:
                        _txt = str(v)
                    ax_trk.text(
                        j, 0, _txt,
                        ha="center", va="center",
                        fontsize=max(fontsize - 2, 3),
                        color=_txt_color,
                        clip_on=True,
                    )

        label = display_names.get(col, col)
        style_track(ax_trk, label, n_samples, fontsize)
        all_axes.append(ax_trk)

        if var_type == "Continuous" and not _tile_color and trk_cmap is not None:
            ax_cb = fig.add_subplot(gs[row_idx, 1])
            ax_cb.set_axis_off()
            valid = num_vals[~np.isnan(num_vals)]
            if len(valid) > 0:
                _ct_sm = ScalarMappable(
                    cmap=trk_cmap,
                    norm=Normalize(
                        vmin=np.nanmin(num_vals), vmax=np.nanmax(num_vals),
                    ),
                )
                cb = fig.colorbar(
                    _ct_sm, ax=ax_cb, fraction=0.9,
                    aspect=8, pad=0.05, location="left",
                )
                cb.ax.tick_params(labelsize=fontsize - 1)
        else:
            fig.add_subplot(gs[row_idx, 1]).set_visible(False)


def render_group_separators(
    group_boundaries, all_axes, label_ax, y_top, n_levels, fontsize,
    draw_labels=True,
):
    """Draw multi-level group separator lines and stacked labels.

    When *draw_labels* is False only the vertical separator lines are drawn;
    the caller is responsible for placing the group labels (e.g. in a figure
    header band). *label_ax*/*y_top* are then ignored.
    """
    if not group_boundaries:
        return

    if n_levels == 1:
        _sep_widths = [1.5]
    else:
        _sep_widths = [
            2.0 - (2.0 - 0.6) * i / (n_levels - 1)
            for i in range(n_levels)
        ]
    _sep_grays = [0, 80, 128, 160]

    for lvl in sorted(group_boundaries):
        w = _sep_widths[min(lvl, len(_sep_widths) - 1)]
        gv = _sep_grays[min(lvl, len(_sep_grays) - 1)]
        color = f"#{gv:02x}{gv:02x}{gv:02x}"
        for (_lbl, start, _end) in group_boundaries[lvl]:
            if start > 0:
                for ax in all_axes:
                    if ax.get_visible():
                        ax.axvline(
                            start - 0.5,
                            color=color,
                            linewidth=w,
                            zorder=10 + (n_levels - lvl),
                        )

    if draw_labels and label_ax is not None:
        for lvl in sorted(group_boundaries):
            row_off = (n_levels - 1 - lvl)
            y_pts = (row_off + 1) * fontsize * 2.0
            for (lbl, start, end) in group_boundaries[lvl]:
                center = (start + end - 1) / 2.0
                label_ax.annotate(
                    lbl,
                    xy=(center, y_top),
                    xytext=(0, y_pts),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=max(fontsize - min(lvl, 2), 5),
                    fontweight="bold" if lvl == 0 else "semibold",
                    clip_on=False,
                )


def build_categorical_legend_handles(
    clinical_cols, clinical_types, clinical_colors,
    clinical_data, track_options, display_names,
):
    """Build legend Patch handles for categorical annotation tracks."""
    handles = []
    if not clinical_cols or clinical_data is None:
        return handles
    for col in clinical_cols:
        if clinical_types.get(col, "Categorical") == "Categorical":
            _opts = track_options.get(col, {})
            if _opts.get("tile_color"):
                continue
            col_map = clinical_colors.get(col, {})
            label_name = display_names.get(col, col)
            vals = sorted(clinical_data[col].dropna().unique(), key=str)
            for i, v in enumerate(vals):
                c = col_map.get(
                    str(v), FALLBACK_COLORS[i % len(FALLBACK_COLORS)]
                )
                handles.append(
                    mpatches.Patch(color=c, label=f"{label_name}: {v}")
                )
    return handles
