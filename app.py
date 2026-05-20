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
        return [to_hex(cmap.colors[i % len(cmap.colors)]) for i in range(n)]
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


def sort_samples(matrix, group_series=None):
    """Waterfall-sort samples.  When *group_series* is provided, sort
    within each group and return boundaries for visual separators.

    Returns ``(sorted_sample_list, OrderedDict {label: (start, end)})``.
    """
    binary = matrix.notna().astype(int).T
    sort_cols = list(binary.columns)

    if group_series is None:
        idx = binary.sort_values(by=sort_cols, ascending=False).index.tolist()
        return idx, OrderedDict()

    groups = group_series.reindex(binary.index)
    unique_groups = list(groups.dropna().unique())

    burden = {}
    for g in unique_groups:
        members = groups[groups == g].index.intersection(binary.index)
        burden[g] = int(binary.loc[members].values.sum())
    sorted_groups = sorted(unique_groups, key=lambda g: -burden.get(g, 0))

    sorted_samples = []
    boundaries = OrderedDict()
    offset = 0
    for g in sorted_groups:
        members = groups[groups == g].index.intersection(binary.index).tolist()
        if not members:
            continue
        sub = binary.loc[members].sort_values(by=sort_cols, ascending=False)
        boundaries[str(g)] = (offset, offset + len(sub))
        sorted_samples.extend(sub.index.tolist())
        offset += len(sub)

    rest = [s for s in binary.index if s not in sorted_samples]
    if rest:
        sub = binary.loc[rest].sort_values(by=sort_cols, ascending=False)
        boundaries["Other"] = (offset, offset + len(sub))
        sorted_samples.extend(sub.index.tolist())

    return sorted_samples, boundaries


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
    group_boundaries = group_boundaries or OrderedDict()

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
    tmb_h = 2.0 if show_tmb else 0.001
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
                cm_name = clinical_colors.get(col, "viridis")
                trk_cmap = _get_cmap(cm_name).copy()
                trk_cmap.set_bad(color="#F0F0F0")
                _ct_masked = np.ma.array(num_vals, mask=np.isnan(num_vals)).reshape(1, -1)
                _ct_x = np.arange(n_samples + 1) - 0.5
                _ct_y = np.array([-0.5, 0.5])
                ax_trk.pcolormesh(
                    _ct_x, _ct_y, _ct_masked,
                    cmap=trk_cmap, edgecolors="white", linewidth=0.3,
                )
                ax_trk.set_ylim(-0.5, 0.5)

            label = display_names.get(col, col)
            _style_track(ax_trk, label, n_samples, fontsize)
            all_axes.append(ax_trk)

            if var_type == "Continuous":
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
        for _grp, (start, _end) in group_boundaries.items():
            if start > 0:
                for ax in all_axes:
                    if ax.get_visible():
                        ax.axvline(
                            start - 0.5,
                            color="black",
                            linewidth=1.5,
                            zorder=10,
                        )
        # Labels above the TMB bar (or above the matrix)
        label_ax = ax_tmb if show_tmb else ax_mat
        ylim = label_ax.get_ylim()
        y_top = max(ylim) if show_tmb else min(ylim)
        for grp, (start, end) in group_boundaries.items():
            center = (start + end - 1) / 2.0
            label_ax.text(
                center,
                y_top,
                str(grp),
                ha="center",
                va="bottom",
                fontsize=fontsize,
                fontweight="bold",
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
                "role_", "disp_", "vt_", "cp_", "cc_",
                "cm_", "dr_cm_", "mc_", "onco_", "matrix_",
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
    data_row_cmaps = {}

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
                vt = st.radio(
                    "Type",
                    ["Categorical", "Continuous"],
                    key=f"vt_{col}",
                )
                annotation_types[col] = vt

                if vt == "Categorical":
                    pal_name = st.selectbox(
                        "Palette",
                        CATEGORICAL_PALETTES,
                        key=f"cp_{col}",
                    )
                    cmap = _get_cmap(pal_name)
                    unique_vals = sorted(
                        df[col].dropna().unique(), key=str,
                    )
                    defaults = _palette_colors(cmap, len(unique_vals))
                    if len(unique_vals) > 15:
                        st.caption(
                            f"Showing top 15 of {len(unique_vals)} values."
                        )
                    color_map = {}
                    for i, val in enumerate(unique_vals[:15]):
                        color_map[val] = st.color_picker(
                            str(val), defaults[i],
                            key=f"cc_{col}_{pal_name}_{val}",
                        )
                    annotation_colors[col] = color_map
                else:
                    cm = st.selectbox(
                        "Colormap",
                        CONTINUOUS_CMAPS,
                        key=f"cm_{col}",
                    )
                    annotation_colors[col] = cm

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
    annot_cols = [c for c, r in col_roles.items() if r == "Annotation Track"]
    drow_cols = [c for c, r in col_roles.items() if r == "Data Row"]

    if len(sample_cols) != 1:
        st.sidebar.error("Assign exactly one column as **Sample ID**.")
        st.stop()
    if len(gene_cols) != 1:
        st.sidebar.error("Assign exactly one column as **Gene / Feature**.")
        st.stop()
    if len(mut_cols) > 1:
        st.sidebar.error("At most one column can be **Mutation Type**.")
        st.stop()

    sample_col = sample_cols[0]
    gene_col = gene_cols[0]
    mut_col = mut_cols[0] if mut_cols else None

    # ── 3. Plot settings (sidebar) ─────────────────────────────
    st.sidebar.header("2 \u2014 Plot Settings")

    exclude = {sample_col, gene_col}
    if mut_col:
        exclude.add(mut_col)
    groupable = ["(None)"] + [c for c in columns if c not in exclude]
    group_col = st.sidebar.selectbox("Group samples by", groupable)
    if group_col == "(None)":
        group_col = None

    n_top_genes = st.sidebar.slider("Top N genes", 5, 50, 20)
    show_tmb = st.sidebar.checkbox("Show Mutation Burden bar", True)
    show_gene_freq = st.sidebar.checkbox("Show Gene Frequency bar", True)
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

    mutation_colors = {}
    n_show = min(20, len(data_mut_types))
    expander_label = (
        f"Edit colours ({n_show} of {len(data_mut_types)})"
        if len(data_mut_types) > n_show
        else "Edit colours"
    )
    with st.sidebar.expander(expander_label, expanded=False):
        # Palette selector
        mc_pal_name = st.selectbox(
            "Palette",
            CATEGORICAL_PALETTES,
            key="mc_palette",
        )
        mc_cmap = _get_cmap(mc_pal_name)
        mc_pal_defaults = _palette_colors(mc_cmap, max(len(data_mut_types), 1))

        # Single-colour toggle
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
    # Assign remaining types not shown in the expander
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
        key_cols = [sample_col, gene_col] + ([mut_col] if mut_col else [])
        clean = df.dropna(subset=key_cols)
        if clean.empty:
            st.error("No valid rows after dropping NaNs in key columns.")
            st.stop()

        n_dropped = len(df) - len(clean)
        if n_dropped:
            st.warning(
                f"Dropped {n_dropped:,} rows with missing values in key columns."
            )

        with st.spinner("Building mutation matrix \u2026"):
            matrix = build_mutation_matrix(clean, sample_col, gene_col, mut_col)
            matrix = matrix.iloc[:n_top_genes]

        # Sample-level data (one row per sample)
        sample_data = clean.drop_duplicates(
            subset=[sample_col],
        ).set_index(sample_col)

        # Group-by
        group_series = None
        if group_col and group_col in sample_data.columns:
            group_series = sample_data[group_col]

        sorted_samples, group_boundaries = sort_samples(
            matrix, group_series,
        )
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

        with st.spinner("Rendering oncoplot \u2026"):
            fig = draw_oncoplot(
                matrix=matrix,
                mutation_colors=mutation_colors,
                clinical_data=clinical_df,
                clinical_cols=annot_cols,
                clinical_types=annotation_types,
                clinical_colors=annotation_colors,
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

        # Cache renderings
        buf_png = BytesIO()
        fig.savefig(buf_png, format="png", dpi=300, bbox_inches="tight")
        st.session_state["onco_png"] = buf_png.getvalue()

        buf_pdf = BytesIO()
        fig.savefig(buf_pdf, format="pdf", bbox_inches="tight")
        st.session_state["onco_pdf"] = buf_pdf.getvalue()

        csv_buf = BytesIO()
        matrix.to_csv(csv_buf)
        st.session_state["matrix_csv"] = csv_buf.getvalue()

        plt.close(fig)

    # ── 6. Display & download ──────────────────────────────────
    if "onco_png" in st.session_state:
        st.image(st.session_state["onco_png"], use_container_width=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button(
                "Download PNG (300 dpi)",
                data=st.session_state["onco_png"],
                file_name="oncoplot.png",
                mime="image/png",
            )
        with c2:
            st.download_button(
                "Download PDF",
                data=st.session_state["onco_pdf"],
                file_name="oncoplot.pdf",
                mime="application/pdf",
            )
        with c3:
            st.download_button(
                "Download Mutation Matrix (CSV)",
                data=st.session_state["matrix_csv"],
                file_name="mutation_matrix.csv",
                mime="text/csv",
            )


if __name__ == "__main__":
    main()
