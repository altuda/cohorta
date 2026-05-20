"""
Oncoplot Builder — Streamlit Application
=========================================
Upload an Excel (.xlsx) mutation dataset, map columns, customise colours,
and generate a publication-quality co-mutation plot.

Run:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from matplotlib.colors import ListedColormap, BoundaryNorm, Normalize, to_hex
from matplotlib.cm import ScalarMappable
from collections import OrderedDict
from io import BytesIO

# ────────────────────────────────────────────────────────────────
# Page configuration
# ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Oncoplot Builder", layout="wide", page_icon="\U0001f9ec",
)

# ────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────
COLUMN_ROLES = [
    "Skip",
    "Sample ID",
    "Gene / Feature",
    "Mutation Type",
    "Annotation Track",
    "Data Row",
]

DEFAULT_MUT_COLORS = {
    "Missense_Mutation":      "#26A269",
    "Nonsense_Mutation":      "#E01B24",
    "Frame_Shift_Del":        "#1A5FB4",
    "Frame_Shift_Ins":        "#613583",
    "Splice_Site":            "#E66100",
    "In_Frame_Del":           "#A51D2D",
    "In_Frame_Ins":           "#C64600",
    "Translation_Start_Site": "#63452C",
    "Nonstop_Mutation":       "#F5C211",
    "Multi_Hit":              "#333333",
}

FALLBACK_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
]

BG_COLOR = "#E8E8E8"

CONTINUOUS_CMAPS = [
    "viridis", "plasma", "inferno", "magma",
    "coolwarm", "RdBu", "YlOrRd", "Blues",
]
CATEGORICAL_PALETTES = [
    "tab10", "Set1", "Set2", "Set3",
    "Pastel1", "Pastel2", "Accent", "Dark2",
]

_SAMPLE_HINTS = [
    "sampleid", "sample_id", "patientid", "patient_id",
    "tumor_sample", "case_id", "subject_id", "barcode", "sample",
]
_GENE_HINTS = [
    "hugo_symbol", "hugo", "gene_name", "gene_symbol",
    "alteration", "feature", "gene",
]
_MUT_HINTS = [
    "variant_classification", "variant_class", "mutation_type",
    "mut_type", "variant_type", "consequence", "vep_consequence",
]


# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────
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


# ────────────────────────────────────────────────────────────────
# Core data functions
# ────────────────────────────────────────────────────────────────
def build_mutation_matrix(df, sample_col, gene_col, mut_col):
    """Build gene x sample mutation matrix from long-format data.

    When *mut_col* is ``None`` each cell value is the gene name so that
    every gene/alteration can receive its own colour.
    """
    if mut_col is None:
        dedup = df.drop_duplicates(subset=[gene_col, sample_col]).copy()
        dedup["_mut"] = dedup[gene_col]
        matrix = dedup.pivot(index=gene_col, columns=sample_col, values="_mut")
    else:
        n_types = (
            df.groupby([gene_col, sample_col])[mut_col]
            .nunique()
            .reset_index(name="_n")
        )
        first_mut = (
            df.groupby([gene_col, sample_col])[mut_col]
            .first()
            .reset_index()
        )
        merged = first_mut.merge(n_types, on=[gene_col, sample_col])
        merged.loc[merged["_n"] > 1, mut_col] = "Multi_Hit"
        matrix = merged.pivot(index=gene_col, columns=sample_col, values=mut_col)

    freq = matrix.notna().sum(axis=1).sort_values(ascending=False)
    return matrix.loc[freq.index]


def sort_samples(matrix, group_series_list=None):
    """Waterfall-sort samples with optional multi-level hierarchical grouping.

    Parameters
    ----------
    matrix : DataFrame or None
        Gene x sample mutation matrix.  ``None`` in annotation-only mode.
    group_series_list : list[Series] or None
        Ordered list of grouping Series (level 0 = outermost).

    Returns
    -------
    sorted_samples : list[str]
    group_boundaries : dict[int, list[tuple[str, int, int]]]
        Keys are level indices.  Values are lists of
        ``(display_label, start_col, end_col)``.
    """
    if matrix is not None:
        binary = matrix.notna().astype(int).T
        sort_cols = list(binary.columns)
        all_samples = binary.index.tolist()
    else:
        binary = None
        sort_cols = []
        all_samples = []
        if group_series_list:
            idx = group_series_list[0].index
            for gs in group_series_list[1:]:
                idx = idx.union(gs.index)
            all_samples = idx.tolist()

    if not group_series_list:
        if binary is not None:
            idx = binary.sort_values(by=sort_cols, ascending=False).index.tolist()
        else:
            idx = all_samples
        return idx, {}

    def _sort_recursive(sample_list, level):
        """Sort *sample_list* by group at *level*, recurse into inner levels."""
        if level >= len(group_series_list):
            # Leaf: waterfall-sort if matrix exists, else keep order
            if binary is not None and sample_list:
                sub = binary.loc[binary.index.intersection(sample_list)]
                return sub.sort_values(
                    by=sort_cols, ascending=False,
                ).index.tolist()
            return list(sample_list)

        gs = group_series_list[level]
        groups = gs.reindex(sample_list)

        unique_groups = list(groups.dropna().unique())
        # Sort groups by mutation burden (desc) or member count
        if binary is not None:
            def _burden(g):
                m = groups[groups == g].index.intersection(binary.index)
                return -int(binary.loc[m].values.sum()) if len(m) else 0
            unique_groups.sort(key=_burden)
        else:
            unique_groups.sort(key=lambda g: -int((groups == g).sum()))

        ordered = []
        boundaries_at_level = []
        offset = len(ordered)  # will be updated via caller

        for g in unique_groups:
            members = groups[groups == g].index.tolist()
            if not members:
                continue
            sub_sorted = _sort_recursive(members, level + 1)
            boundaries_at_level.append((str(g), len(ordered), len(ordered) + len(sub_sorted)))
            ordered.extend(sub_sorted)

        # Samples with NaN at this level
        rest = [s for s in sample_list if s not in set(ordered)]
        if rest:
            sub_sorted = _sort_recursive(rest, level + 1)
            boundaries_at_level.append(("Other", len(ordered), len(ordered) + len(sub_sorted)))
            ordered.extend(sub_sorted)

        return ordered, boundaries_at_level

    # Run recursive sort from level 0
    # We need boundaries at ALL levels, so run per-level boundary collection
    # Pre-compute a global sort rank for every level so that inner
    # groups keep the same order across all parent groups.
    _global_rank = {}
    for _lvl, _gs in enumerate(group_series_list):
        _uvals = list(_gs.dropna().unique())
        if binary is not None:
            def _global_burden(g, _s=_gs):
                m = _s[_s == g].index.intersection(binary.index)
                return -int(binary.loc[m].values.sum()) if len(m) else 0
            _uvals.sort(key=_global_burden)
        else:
            def _global_count(g, _s=_gs):
                return -int((_s == g).sum())
            _uvals.sort(key=_global_count)
        _global_rank[_lvl] = {g: i for i, g in enumerate(_uvals)}

    sorted_samples = []
    all_boundaries = {}

    def _collect(sample_list, level, global_offset):
        """Sort and collect boundaries at all levels."""
        if level >= len(group_series_list):
            if binary is not None and sample_list:
                sub = binary.loc[binary.index.intersection(sample_list)]
                return sub.sort_values(
                    by=sort_cols, ascending=False,
                ).index.tolist()
            return list(sample_list)

        gs = group_series_list[level]
        groups = gs.reindex(sample_list)
        unique_groups = list(groups.dropna().unique())

        rank = _global_rank.get(level, {})
        unique_groups.sort(key=lambda g: rank.get(g, 999))

        ordered = []
        local_offset = 0

        for g in unique_groups:
            members = groups[groups == g].index.tolist()
            if not members:
                continue
            sub_sorted = _collect(members, level + 1, global_offset + local_offset)
            all_boundaries.setdefault(level, []).append(
                (str(g), global_offset + local_offset,
                 global_offset + local_offset + len(sub_sorted))
            )
            ordered.extend(sub_sorted)
            local_offset += len(sub_sorted)

        rest = [s for s in sample_list if s not in set(ordered)]
        if rest:
            sub_sorted = _collect(rest, level + 1, global_offset + local_offset)
            all_boundaries.setdefault(level, []).append(
                ("Other", global_offset + local_offset,
                 global_offset + local_offset + len(sub_sorted))
            )
            ordered.extend(sub_sorted)

        return ordered

    sorted_samples = _collect(all_samples, 0, 0)
    return sorted_samples, all_boundaries


# ────────────────────────────────────────────────────────────────
# Plotting
# ────────────────────────────────────────────────────────────────
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

    # ── Mutation type -> integer mapping for imshow ─────────────
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
    _grp_label_h = _n_grp_levels * fontsize * 2.5 / 72  # extra space for stacked labels
    tmb_h = (2.0 if show_tmb else 0.001) + _grp_label_h
    mat_h = max(n_genes * 0.45, 3.0)
    data_h = 0.6
    trk_h = 0.6
    # Reserve space between matrix and tracks/data-rows
    gap_h = 0.25 if (n_data + n_tracks) > 0 else 0.0
    has_gap = gap_h > 0

    # Estimate height needed for rotated sample labels
    _labels_visible = show_sample_labels and n_samples <= 80
    _labels_on_top = _labels_visible and annotations_position == "bottom"
    _labels_on_bottom = _labels_visible and annotations_position == "top"
    if _labels_visible:
        _max_lbl = max((len(str(s)) for s in samples), default=0)
        _label_h = min(2.5, _max_lbl * max(fontsize - 2, 4) * 0.5 / 72)
    else:
        _label_h = 0.0

    # Row layout depends on annotation position
    if annotations_position == "top":
        # TMB | tracks | data rows | gap | matrix
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
        # TMB | (label spacer?) | matrix | gap | data rows | tracks
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

    all_axes = []  # axes sharing the x (sample) axis

    # ── 1. TMB stacked bar ─────────────────────────────────────
    ax_tmb = fig.add_subplot(gs[tmb_row, 0])
    all_axes.append(ax_tmb)
    if show_tmb:
        bottom = np.zeros(n_samples)
        for mt in all_mut_types:
            counts = (matrix == mt).sum(axis=0).values.astype(float)
            ax_tmb.bar(
                np.arange(n_samples),
                counts,
                bottom=bottom,
                color=mutation_colors.get(mt, "#808080"),
                width=1.0,
                linewidth=0,
            )
            bottom += counts
        ax_tmb.set_xlim(-0.5, n_samples - 0.5)
        ax_tmb.set_ylabel("TMB", fontsize=fontsize)
        ax_tmb.tick_params(axis="x", bottom=False, labelbottom=False)
        ax_tmb.tick_params(axis="y", labelsize=fontsize - 1)
        ax_tmb.spines[["top", "right", "bottom"]].set_visible(False)
    else:
        ax_tmb.set_visible(False)

    fig.add_subplot(gs[tmb_row, 1]).set_visible(False)

    # Hidden spacer for sample labels extending above the matrix
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

    # Sample labels on the opposite side from annotations
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

    # ── Spacer between matrix and tracks ──────────────────────
    if gap_row is not None:
        ax_gap = fig.add_subplot(gs[gap_row, 0])
        ax_gap.set_visible(False)
        fig.add_subplot(gs[gap_row, 1]).set_visible(False)

    def _style_track(ax, label, n_samples, fontsize):
        """Apply consistent styling to data-row / annotation-track axes."""
        # Cell borders
        for j in range(n_samples + 1):
            ax.axvline(j - 0.5, color="white", linewidth=0.3)
        # Subtle frame
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_linewidth(0.4)
            spine.set_color("#999999")
        ax.set_yticks([0])
        ax.set_yticklabels([label], fontsize=fontsize, fontweight="semibold")
        ax.tick_params(axis="x", bottom=False, labelbottom=False)
        ax.tick_params(axis="y", length=0)
        ax.set_xlim(-0.5, n_samples - 0.5)

    # ── 4. Data rows (in-plot heatmaps) ────────────────────────
    if data_rows:
        for dr_idx, (dr_col, dr_values) in enumerate(data_rows.items()):
            row_idx = data_start + dr_idx
            ax_dr = fig.add_subplot(gs[row_idx, 0], sharex=ax_mat)
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
            _style_track(ax_dr, label, n_samples, fontsize)
            all_axes.append(ax_dr)

            ax_cb = fig.add_subplot(gs[row_idx, 1])
            ax_cb.set_axis_off()
            valid = vals[~np.isnan(vals)]
            if len(valid) > 0:
                _dr_sm = ScalarMappable(
                    cmap=dr_cmap,
                    norm=Normalize(vmin=np.nanmin(vals), vmax=np.nanmax(vals)),
                )
                cb = fig.colorbar(_dr_sm, ax=ax_cb, fraction=0.9, aspect=8,
                                  pad=0.05, location="left")
                cb.ax.tick_params(labelsize=fontsize - 1)

    # ── 5. Annotation tracks ──────────────────────────────────
    if clinical_cols and clinical_data is not None:
        for t_idx, col in enumerate(clinical_cols):
            row_idx = trk_start + t_idx
            ax_trk = fig.add_subplot(gs[row_idx, 0], sharex=ax_mat)
            values = clinical_data.reindex(samples)[col]
            var_type = clinical_types.get(col, "Categorical")
            _opts = track_options.get(col, {})
            _tile_color = _opts.get("tile_color")

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
                    tc_list = [
                        col_map.get(
                            v, FALLBACK_COLORS[i % len(FALLBACK_COLORS)]
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
            else:
                num_vals = (
                    pd.to_numeric(values, errors="coerce")
                    .values.astype(float)
                )
                _ct_x = np.arange(n_samples + 1) - 0.5
                _ct_y = np.array([-0.5, 0.5])
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
            _style_track(ax_trk, label, n_samples, fontsize)
            all_axes.append(ax_trk)

            if var_type == "Continuous" and not _tile_color:
                ax_cb = fig.add_subplot(gs[row_idx, 1])
                ax_cb.set_axis_off()
                valid = num_vals[~np.isnan(num_vals)]
                if len(valid) > 0:
                    _ct_sm = ScalarMappable(
                        cmap=trk_cmap,
                        norm=Normalize(vmin=np.nanmin(num_vals), vmax=np.nanmax(num_vals)),
                    )
                    cb = fig.colorbar(_ct_sm, ax=ax_cb, fraction=0.9,
                                      aspect=8, pad=0.05, location="left")
                    cb.ax.tick_params(labelsize=fontsize - 1)
            else:
                fig.add_subplot(gs[row_idx, 1]).set_visible(False)

    # ── 6. Group separators & labels ───────────────────────────
    if group_boundaries:
        n_levels = len(group_boundaries)
        # Separator widths: outer = thick, inner = thin
        if n_levels == 1:
            _sep_widths = [1.5]
        else:
            _sep_widths = [
                2.0 - (2.0 - 0.6) * i / (n_levels - 1)
                for i in range(n_levels)
            ]
        _sep_grays = [0, 80, 128, 160]  # up to 4 levels

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

        # Stacked labels above TMB / matrix
        label_ax = ax_tmb if show_tmb else ax_mat
        ylim = label_ax.get_ylim()
        y_top = max(ylim) if show_tmb else min(ylim)

        for lvl in sorted(group_boundaries):
            # Outermost level = highest offset
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

    # ── 7. Legend ──────────────────────────────────────────────
    legend_handles = [
        mpatches.Patch(color=mutation_colors.get(mt, "#808080"), label=mt)
        for mt in all_mut_types
    ]
    if clinical_cols and clinical_data is not None:
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
                        v, FALLBACK_COLORS[i % len(FALLBACK_COLORS)]
                    )
                    legend_handles.append(
                        mpatches.Patch(
                            color=c, label=f"{label_name}: {v}"
                        )
                    )

    # Compute dynamic bottom margin so the legend never overlaps the plot
    n_legend_cols = min(5, len(legend_handles)) if legend_handles else 1
    n_legend_rows = (
        (len(legend_handles) + n_legend_cols - 1) // n_legend_cols
        if legend_handles
        else 0
    )
    # Convert legend row height (≈ fontsize * 1.8 pt) to figure fraction
    row_frac = (fontsize * 1.8) / (fig_height * 72) if fig_height > 0 else 0
    legend_margin = n_legend_rows * row_frac * 1.4  # 1.4× padding
    _bottom_lbl = (_label_h / fig_height) if _labels_on_bottom and fig_height > 0 else 0
    bottom = min(0.50, max(0.06, 0.02 + legend_margin + _bottom_lbl))

    if legend_handles:
        fig.legend(
            handles=legend_handles,
            loc="upper center",
            ncol=n_legend_cols,
            fontsize=fontsize - 1,
            frameon=False,
            bbox_to_anchor=(0.45, bottom - 0.005 - _bottom_lbl),
            handlelength=1.2,
            handleheight=1.0,
            columnspacing=1.0,
        )

    if title is not None:
        fig.suptitle(
            title,
            fontsize=fontsize + 3,
            fontweight="bold",
            y=0.99,
        )
    fig.subplots_adjust(
        left=0.08, right=0.95, top=0.94, bottom=bottom,
    )
    return fig


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
    ax_hdr = fig.add_subplot(gs[header_row, 0])
    ax_hdr.set_xlim(-0.5, n_samples - 0.5)
    ax_hdr.set_visible(False)
    fig.add_subplot(gs[header_row, 1]).set_visible(False)

    def _style_trk(ax, label):
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

    _first_ax = None

    # ── Data rows ───────────────────────────────────────────────
    if data_rows:
        for dr_idx, (dr_col, dr_values) in enumerate(data_rows.items()):
            row_idx = data_start + dr_idx
            ax_dr = fig.add_subplot(gs[row_idx, 0])
            if _first_ax is None:
                _first_ax = ax_dr
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
            _style_trk(ax_dr, label)
            all_axes.append(ax_dr)

            ax_cb = fig.add_subplot(gs[row_idx, 1])
            ax_cb.set_axis_off()
            valid = vals[~np.isnan(vals)]
            if len(valid) > 0:
                _dr_sm = ScalarMappable(
                    cmap=dr_cmap,
                    norm=Normalize(vmin=np.nanmin(vals), vmax=np.nanmax(vals)),
                )
                cb = fig.colorbar(_dr_sm, ax=ax_cb, fraction=0.9, aspect=8,
                                  pad=0.05, location="left")
                cb.ax.tick_params(labelsize=fontsize - 1)

    # ── Annotation tracks ───────────────────────────────────────
    if clinical_cols and clinical_data is not None:
        for t_idx, col in enumerate(clinical_cols):
            row_idx = trk_start + t_idx
            ax_trk = fig.add_subplot(gs[row_idx, 0])
            if _first_ax is None:
                _first_ax = ax_trk
            values = clinical_data.reindex(samples)[col]
            var_type = clinical_types.get(col, "Categorical")
            _opts = track_options.get(col, {})
            _tile_color = _opts.get("tile_color")

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
                    tc_list = [
                        col_map.get(
                            v, FALLBACK_COLORS[i % len(FALLBACK_COLORS)]
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
            else:
                num_vals = (
                    pd.to_numeric(values, errors="coerce")
                    .values.astype(float)
                )
                _ct_x = np.arange(n_samples + 1) - 0.5
                _ct_y = np.array([-0.5, 0.5])
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
            _style_trk(ax_trk, label)
            all_axes.append(ax_trk)

            if var_type == "Continuous" and not _tile_color:
                ax_cb = fig.add_subplot(gs[row_idx, 1])
                ax_cb.set_axis_off()
                valid = num_vals[~np.isnan(num_vals)]
                if len(valid) > 0:
                    _ct_sm = ScalarMappable(
                        cmap=trk_cmap,
                        norm=Normalize(vmin=np.nanmin(num_vals),
                                       vmax=np.nanmax(num_vals)),
                    )
                    cb = fig.colorbar(_ct_sm, ax=ax_cb, fraction=0.9,
                                      aspect=8, pad=0.05, location="left")
                    cb.ax.tick_params(labelsize=fontsize - 1)
            else:
                fig.add_subplot(gs[row_idx, 1]).set_visible(False)

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
    if group_boundaries:
        n_levels = len(group_boundaries)
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

        # Stacked labels above first visible axis
        label_ax = _first_ax
        if label_ax is not None:
            ylim = label_ax.get_ylim()
            y_top = max(ylim)
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

    # ── Legend ───────────────────────────────────────────────────
    legend_handles = []
    if clinical_cols and clinical_data is not None:
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
                        v, FALLBACK_COLORS[i % len(FALLBACK_COLORS)]
                    )
                    legend_handles.append(
                        mpatches.Patch(color=c, label=f"{label_name}: {v}")
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


# ────────────────────────────────────────────────────────────────
# Main Streamlit application
# ────────────────────────────────────────────────────────────────
def main():
    st.title("\U0001f9ec Oncoplot Builder")
    st.markdown(
        "Upload a mutation dataset (`.xlsx`), map columns, customise "
        "colours, and generate a publication-quality co-mutation plot."
    )

    # ── 1. File upload ─────────────────────────────────────────
    uploaded = st.file_uploader("Upload Excel file (.xlsx)", type=["xlsx"])
    if uploaded is None:
        st.info("Upload an `.xlsx` file to begin.")
        st.stop()

    # Invalidate state when file changes
    if (
        "uploaded_name" not in st.session_state
        or st.session_state["uploaded_name"] != uploaded.name
    ):
        st.session_state["uploaded_name"] = uploaded.name
        for k in list(st.session_state.keys()):
            if k.startswith((
                "role_", "disp_", "vt_", "cp_", "cc_", "ci_",
                "cm_", "dr_cm_", "mc_", "onco_", "matrix_", "ao_",
            )):
                del st.session_state[k]

    df = pd.read_excel(uploaded, engine="openpyxl")
    st.success(
        f"Loaded **{len(df):,}** rows  \u00d7  **{len(df.columns)}** columns."
    )
    with st.expander("Preview raw data", expanded=True):
        st.dataframe(df.head(5), use_container_width=True)

    columns = df.columns.tolist()
    guessed = _auto_assign_roles(columns)

    # ── 2. Column configuration (sidebar) ──────────────────────
    st.sidebar.header("1 \u2014 Column Configuration")

    col_roles = {}
    col_display = {}
    annotation_types = {}
    annotation_colors = {}
    annotation_order = {}
    track_options = {}
    data_row_cmaps = {}
    _annot_count = 0

    for col in columns:
        g = guessed.get(col, "Skip")
        with st.sidebar.expander(col, expanded=(g != "Skip")):
            role = st.selectbox(
                "Role",
                COLUMN_ROLES,
                index=COLUMN_ROLES.index(g),
                key=f"role_{col}",
            )
            display = st.text_input(
                "Display name", col, key=f"disp_{col}",
            )
            col_roles[col] = role
            col_display[col] = display

            # --- Annotation Track options ---
            if role == "Annotation Track":
                _annot_count += 1
                vt = st.radio(
                    "Type",
                    ["Categorical", "Continuous"],
                    key=f"vt_{col}",
                )
                annotation_types[col] = vt

                _ao = st.number_input(
                    "Display order", min_value=1,
                    value=_annot_count, key=f"ao_{col}",
                )
                annotation_order[col] = _ao

                # --- Track tile / text options ---
                _use_tile = st.checkbox(
                    "Use single tile colour", key=f"ut_{col}",
                )
                _tile_col = None
                if _use_tile:
                    _tile_col = st.color_picker(
                        "Tile colour", "#E0E0E0", key=f"tlc_{col}",
                    )

                if vt == "Categorical":
                    if not _use_tile:
                        pal_name = st.selectbox(
                            "Palette",
                            CATEGORICAL_PALETTES,
                            key=f"cp_{col}",
                        )
                        cmap = _get_cmap(pal_name)
                        n_pal = (
                            len(cmap.colors)
                            if hasattr(cmap, "colors")
                            else 10
                        )
                        all_pal = _palette_colors(cmap, n_pal)

                        # Palette colour swatches (numbered)
                        _pcols = st.columns(n_pal)
                        for _pi, _pc in enumerate(all_pal):
                            _pcols[_pi].markdown(
                                f'<div style="background:{_pc};'
                                f"height:22px;border-radius:3px;"
                                f"text-align:center;color:#fff;"
                                f"font-size:11px;line-height:22px;"
                                f"font-weight:600;"
                                f'text-shadow:0 0 2px rgba(0,0,0,.6)">'
                                f"{_pi + 1}</div>",
                                unsafe_allow_html=True,
                            )

                        unique_vals = sorted(
                            df[col].dropna().unique(), key=str,
                        )
                        _spread = np.linspace(
                            0, n_pal - 1, len(unique_vals),
                            dtype=int,
                        ).tolist()
                        if len(unique_vals) > 15:
                            st.caption(
                                f"Showing top 15 of "
                                f"{len(unique_vals)} values."
                            )
                        color_map = {}
                        _radio_labels = (
                            [str(j + 1) for j in range(n_pal)]
                            + ["\u270e"]
                        )
                        for i, val in enumerate(unique_vals[:15]):
                            _def = (
                                _spread[i]
                                if i < len(_spread)
                                else 0
                            )
                            _pick = st.radio(
                                str(val),
                                _radio_labels,
                                index=_def,
                                horizontal=True,
                                key=f"ci_{col}_{pal_name}_{val}",
                            )
                            if _pick == "\u270e":
                                color_map[val] = st.color_picker(
                                    f"Custom for {val}",
                                    all_pal[_def],
                                    key=f"cc_{col}_{pal_name}_{val}",
                                )
                            else:
                                _idx = int(_pick) - 1
                                color_map[val] = all_pal[_idx]
                                st.markdown(
                                    f'<div style="background:'
                                    f"{all_pal[_idx]};"
                                    f"height:6px;border-radius:3px;"
                                    f'margin-top:-8px;"></div>',
                                    unsafe_allow_html=True,
                                )
                        annotation_colors[col] = color_map
                    else:
                        annotation_colors[col] = {}
                else:
                    if not _use_tile:
                        cm = st.selectbox(
                            "Colormap",
                            CONTINUOUS_CMAPS,
                            key=f"cm_{col}",
                        )
                        annotation_colors[col] = cm
                    else:
                        annotation_colors[col] = "viridis"

                _show_vals = st.checkbox(
                    "Show values in tiles", key=f"sv_{col}",
                )
                _txt_col = "#000000"
                if _show_vals:
                    _txt_col = st.color_picker(
                        "Text colour", "#000000", key=f"tc_{col}",
                    )
                track_options[col] = {
                    "show_values": _show_vals,
                    "text_color": _txt_col,
                    "tile_color": _tile_col,
                }

            # --- Data Row options ---
            elif role == "Data Row":
                cm = st.selectbox(
                    "Colormap",
                    CONTINUOUS_CMAPS,
                    key=f"dr_cm_{col}",
                )
                data_row_cmaps[col] = cm

    # ── Derive logical columns ─────────────────────────────────
    sample_cols = [c for c, r in col_roles.items() if r == "Sample ID"]
    gene_cols = [c for c, r in col_roles.items() if r == "Gene / Feature"]
    mut_cols = [c for c, r in col_roles.items() if r == "Mutation Type"]
    annot_cols = sorted(
        [c for c, r in col_roles.items() if r == "Annotation Track"],
        key=lambda c: annotation_order.get(c, 0),
    )
    drow_cols = [c for c, r in col_roles.items() if r == "Data Row"]

    if len(sample_cols) != 1:
        st.sidebar.error("Assign exactly one column as **Sample ID**.")
        st.stop()
    if len(gene_cols) > 1:
        st.sidebar.error("At most one column can be **Gene / Feature**.")
        st.stop()
    if len(mut_cols) > 1:
        st.sidebar.error("At most one column can be **Mutation Type**.")
        st.stop()

    sample_col = sample_cols[0]
    gene_col = gene_cols[0] if gene_cols else None
    mut_col = mut_cols[0] if mut_cols else None

    if mut_col and not gene_col:
        st.sidebar.error("**Mutation Type** requires a **Gene / Feature** column.")
        st.stop()

    # ── 3. Plot settings (sidebar) ─────────────────────────────
    st.sidebar.header("2 \u2014 Plot Settings")

    exclude = {sample_col}
    if gene_col:
        exclude.add(gene_col)
    if mut_col:
        exclude.add(mut_col)
    groupable = [c for c in columns if c not in exclude]

    n_group_levels = st.sidebar.number_input(
        "Grouping levels", min_value=0, max_value=4, value=0,
        key="onco_n_grp",
    )
    group_cols = []
    _used_grp = set()
    for _lvl in range(n_group_levels):
        _avail = ["(None)"] + [c for c in groupable if c not in _used_grp]
        _chosen = st.sidebar.selectbox(
            f"Group level {_lvl + 1}", _avail, key=f"onco_grp_{_lvl}",
        )
        if _chosen != "(None)":
            group_cols.append(_chosen)
            _used_grp.add(_chosen)

    if gene_col is not None:
        n_top_genes = st.sidebar.slider("Top N genes", 5, 50, 20)
        show_tmb = st.sidebar.checkbox("Show Mutation Burden bar", True)
        show_gene_freq = st.sidebar.checkbox("Show Gene Frequency bar", True)
    else:
        n_top_genes = 0
        show_tmb = False
        show_gene_freq = False
    show_sample_labels = st.sidebar.checkbox("Show sample labels", False)
    annot_pos = st.sidebar.radio(
        "Annotation position", ["Bottom", "Top"], key="onco_annot_pos",
    )
    show_title = st.sidebar.checkbox("Show title", True)
    plot_title = st.sidebar.text_input(
        "Title", "Oncoplot", key="onco_title",
    ) if show_title else None
    fig_width = st.sidebar.slider("Figure width (in)", 8, 30, 14)
    fontsize = st.sidebar.slider("Font size", 5, 14, 8)

    # ── 4. Mutation / gene colours (sidebar) ───────────────────
    mutation_colors = {}
    if gene_col is not None:
        if mut_col is None:
            st.sidebar.header("3 \u2014 Gene / Alteration Colours")
            gene_freq = df[gene_col].value_counts()
            data_mut_types = gene_freq.index.tolist()
        else:
            st.sidebar.header("3 \u2014 Mutation Type Colours")
            data_mut_types = list(df[mut_col].dropna().unique())
            has_multi = (
                df.groupby([gene_col, sample_col])[mut_col].nunique().max() > 1
            )
            if has_multi and "Multi_Hit" not in data_mut_types:
                data_mut_types.append("Multi_Hit")
            data_mut_types = sorted(set(data_mut_types), key=str)

        n_show = min(20, len(data_mut_types))
        expander_label = (
            f"Edit colours ({n_show} of {len(data_mut_types)})"
            if len(data_mut_types) > n_show
            else "Edit colours"
        )
        with st.sidebar.expander(expander_label, expanded=False):
            mc_pal_name = st.selectbox(
                "Palette",
                CATEGORICAL_PALETTES,
                key="mc_palette",
            )
            mc_cmap = _get_cmap(mc_pal_name)
            mc_pal_defaults = _palette_colors(mc_cmap, max(len(data_mut_types), 1))

            use_single = st.checkbox("Use single colour", key="mc_single_color")

            if use_single:
                single_color = st.color_picker(
                    "Colour for all types",
                    mc_pal_defaults[0],
                    key=f"mc_{mc_pal_name}_single",
                )
                for mt in data_mut_types:
                    mutation_colors[mt] = single_color
            else:
                for idx, mt in enumerate(data_mut_types[:n_show]):
                    default = DEFAULT_MUT_COLORS.get(
                        mt, mc_pal_defaults[idx % len(mc_pal_defaults)],
                    )
                    mutation_colors[mt] = st.color_picker(
                        mt, default, key=f"mc_{mc_pal_name}_{mt}",
                    )
        for idx, mt in enumerate(data_mut_types):
            if mt not in mutation_colors:
                if use_single:
                    mutation_colors[mt] = single_color
                else:
                    mutation_colors[mt] = DEFAULT_MUT_COLORS.get(
                        mt, mc_pal_defaults[idx % len(mc_pal_defaults)],
                    )

    # ── 5. Generate oncoplot ───────────────────────────────────
    st.divider()
    generate = st.button(
        "Generate Oncoplot", type="primary", use_container_width=True,
    )

    if generate:
        if gene_col is not None:
            # ── Standard mode: build mutation matrix ────────────
            key_cols = [sample_col, gene_col] + ([mut_col] if mut_col else [])
            clean = df.dropna(subset=key_cols)
            if clean.empty:
                st.error("No valid rows after dropping NaNs in key columns.")
                st.stop()

            n_dropped = len(df) - len(clean)
            if n_dropped:
                st.warning(
                    f"Dropped {n_dropped:,} rows with missing values in "
                    "key columns."
                )

            with st.spinner("Building mutation matrix \u2026"):
                matrix = build_mutation_matrix(
                    clean, sample_col, gene_col, mut_col,
                )
                matrix = matrix.iloc[:n_top_genes]

            sample_data = clean.drop_duplicates(
                subset=[sample_col],
            ).set_index(sample_col)
        else:
            # ── Annotation-only mode ────────────────────────────
            matrix = None
            sample_data = df.drop_duplicates(
                subset=[sample_col],
            ).set_index(sample_col)

        # Group-by
        group_series_list = []
        for _gc in group_cols:
            if _gc in sample_data.columns:
                group_series_list.append(sample_data[_gc])

        sorted_samples, group_boundaries = sort_samples(
            matrix, group_series_list if group_series_list else None,
        )
        # Fallback: annotation-only with no groups → use all samples
        if not sorted_samples and matrix is None:
            sorted_samples = sample_data.index.tolist()
        if matrix is not None:
            matrix = matrix.reindex(columns=sorted_samples)

        # Clinical / annotation data
        clinical_df = sample_data[annot_cols] if annot_cols else None

        # Data rows
        dr_dict = OrderedDict()
        for drc in drow_cols:
            if drc in sample_data.columns:
                dr_dict[drc] = pd.to_numeric(
                    sample_data[drc], errors="coerce",
                )

        if matrix is not None:
            with st.spinner("Rendering oncoplot \u2026"):
                fig = draw_oncoplot(
                    matrix=matrix,
                    mutation_colors=mutation_colors,
                    clinical_data=clinical_df,
                    clinical_cols=annot_cols,
                    clinical_types=annotation_types,
                    clinical_colors=annotation_colors,
                    track_options=track_options,
                    data_rows=dr_dict,
                    data_row_cmaps=data_row_cmaps,
                    display_names=col_display,
                    group_boundaries=group_boundaries,
                    show_tmb=show_tmb,
                    show_gene_freq=show_gene_freq,
                    show_sample_labels=show_sample_labels,
                    annotations_position=annot_pos.lower(),
                    title=plot_title,
                    fig_width=fig_width,
                    fontsize=fontsize,
                )
        else:
            if not annot_cols and not drow_cols:
                st.error(
                    "Assign at least one **Annotation Track** or "
                    "**Data Row** in annotation-only mode."
                )
                st.stop()
            with st.spinner("Rendering annotation plot \u2026"):
                fig = draw_annotation_plot(
                    samples=sorted_samples,
                    clinical_data=clinical_df,
                    clinical_cols=annot_cols,
                    clinical_types=annotation_types,
                    clinical_colors=annotation_colors,
                    track_options=track_options,
                    data_rows=dr_dict,
                    data_row_cmaps=data_row_cmaps,
                    display_names=col_display,
                    group_boundaries=group_boundaries,
                    show_sample_labels=show_sample_labels,
                    title=plot_title,
                    fig_width=fig_width,
                    fontsize=fontsize,
                )

        # Cache renderings
        buf_png = BytesIO()
        fig.savefig(buf_png, format="png", dpi=300, bbox_inches="tight")
        st.session_state["onco_png"] = buf_png.getvalue()

        buf_pdf = BytesIO()
        fig.savefig(buf_pdf, format="pdf", bbox_inches="tight")
        st.session_state["onco_pdf"] = buf_pdf.getvalue()

        if matrix is not None:
            csv_buf = BytesIO()
            matrix.to_csv(csv_buf)
            st.session_state["matrix_csv"] = csv_buf.getvalue()
        else:
            st.session_state.pop("matrix_csv", None)

        plt.close(fig)

    # ── 6. Display & download ──────────────────────────────────
    if "onco_png" in st.session_state:
        st.image(st.session_state["onco_png"], use_container_width=True)

        _has_csv = "matrix_csv" in st.session_state
        cols = st.columns(3 if _has_csv else 2)
        with cols[0]:
            st.download_button(
                "Download PNG (300 dpi)",
                data=st.session_state["onco_png"],
                file_name="oncoplot.png",
                mime="image/png",
            )
        with cols[1]:
            st.download_button(
                "Download PDF",
                data=st.session_state["onco_pdf"],
                file_name="oncoplot.pdf",
                mime="application/pdf",
            )
        if _has_csv:
            with cols[2]:
                st.download_button(
                    "Download Mutation Matrix (CSV)",
                    data=st.session_state["matrix_csv"],
                    file_name="mutation_matrix.csv",
                    mime="text/csv",
                )


if __name__ == "__main__":
    main()
