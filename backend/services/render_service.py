"""Render service: orchestrates oncoplot_core calls."""

from __future__ import annotations

import hashlib
import json
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from oncoplot_core import (
    build_mutation_matrix, sort_samples,
    draw_oncoplot, draw_annotation_plot,
    DEFAULT_MUT_COLORS, NONSYNONYMOUS_CLASSES, MIN_TMB_PANEL_MB,
)

from ..session_store import SessionData
from ..models import RenderRequest


# Resolution of the on-screen preview PNG. Print-quality 300 DPI is reserved
# for the download (built lazily); the live preview only needs screen pixels.
PREVIEW_DPI = 110
EXPORT_DPI = 300


def _config_hash(req: RenderRequest) -> str:
    raw = req.model_dump_json(exclude_none=False)
    return hashlib.md5(raw.encode()).hexdigest()


def _build_figure(session: SessionData, req: RenderRequest):
    """Build the matplotlib figure for *req*.

    Returns ``(fig, matrix, warnings)``. This is the expensive step shared by the
    interactive preview and the lazy hi-res / PDF exports.
    """
    df = session.df
    roles = req.roles
    warnings = []

    # Extract column assignments
    sample_col = next((c for c, r in roles.items() if r == "Sample ID"), None)
    gene_col = next((c for c, r in roles.items() if r == "Gene / Feature"), None)
    mut_col = next((c for c, r in roles.items() if r == "Mutation Type"), None)
    annot_cols = req.annotation_order or [
        c for c, r in roles.items() if r == "Annotation Track"
    ]

    if sample_col is None:
        raise ValueError("No Sample ID column assigned.")

    # Clean data
    if gene_col is not None:
        key_cols = [sample_col, gene_col] + ([mut_col] if mut_col else [])
        clean = df.dropna(subset=key_cols)
        n_dropped = len(df) - len(clean)
        if n_dropped:
            warnings.append(f"Dropped {n_dropped:,} rows with missing values in key columns.")
        if clean.empty:
            raise ValueError("No valid rows after dropping NaNs in key columns.")

        matrix = build_mutation_matrix(clean, sample_col, gene_col, mut_col)
        matrix = matrix.iloc[:req.top_n_genes]

        # Per-sample mutation burden over the FULL dataset (every gene, not just
        # the displayed top-N), stacked by mutation type. This is the real
        # per-sample mutation count; the displayed-genes matrix would massively
        # undercount it. "Multi_Hit" is a per-cell display artifact, so the
        # burden counts each variant by its actual classification instead.
        # Only non-synonymous (protein-altering) classes count, per the
        # cBioPortal/MSK convention; silent/synonymous variants are excluded.
        if mut_col is not None:
            _cls = clean[mut_col].astype(str).str.lower()
            burden_src = clean[_cls.isin(NONSYNONYMOUS_CLASSES)]
            if burden_src.empty:
                warnings.append(
                    "No standard non-synonymous variant classifications were "
                    "recognized; mutation burden counts all variant types."
                )
                burden_src = clean
            mutation_burden = (
                burden_src.groupby([sample_col, mut_col])
                .size().unstack(fill_value=0)
            )
        else:
            # Gene-as-colour mode: count distinct altered genes per sample.
            mutation_burden = (
                clean.drop_duplicates(subset=[sample_col, gene_col])
                .groupby([sample_col, gene_col]).size()
                .unstack(fill_value=0)
            )

        sample_data = clean.drop_duplicates(subset=[sample_col]).set_index(sample_col)
    else:
        matrix = None
        mutation_burden = None
        sample_data = df.drop_duplicates(subset=[sample_col]).set_index(sample_col)

    # Group-by (with optional custom per-level block order or numeric sort)
    group_series_list = []
    group_orders = []
    group_sort_modes = []
    for gc in req.group_columns:
        if gc in sample_data.columns:
            group_series_list.append(sample_data[gc])
            group_orders.append(req.group_order.get(gc))
            group_sort_modes.append(req.group_sort.get(gc))

    sorted_samples, group_boundaries = sort_samples(
        matrix, group_series_list if group_series_list else None,
        group_orders=group_orders if group_series_list else None,
        group_sort_modes=group_sort_modes if group_series_list else None,
    )
    if not sorted_samples and matrix is None:
        sorted_samples = sample_data.index.tolist()
    if matrix is not None:
        matrix = matrix.reindex(columns=sorted_samples)

    # Clinical / annotation data
    clinical_df = sample_data[annot_cols] if annot_cols else None

    # Track options: convert from Pydantic to plain dict
    track_opts = {
        col: {
            "show_values": opts.show_values,
            "text_color": opts.text_color,
            "tile_color": opts.tile_color,
            "value_plot": opts.value_plot,
            "plot_color": opts.plot_color,
            "plot_size": opts.plot_size,
            "position": opts.position,
        }
        for col, opts in req.track_options.items()
    }

    # Mutation colors: apply defaults for missing types. Cover both the matrix
    # types (heatmap/legend) and any burden-only classes so the top bar segments
    # always have a defined colour.
    mutation_colors = dict(req.mutation_colors)
    if matrix is not None:
        all_types = [t for t in matrix.stack().unique() if pd.notna(t)]
        if mutation_burden is not None:
            all_types = all_types + list(mutation_burden.columns)
        for mt in sorted(set(all_types), key=str):
            if mt not in mutation_colors:
                mutation_colors[mt] = DEFAULT_MUT_COLORS.get(mt, "#808080")

    # TMB: only express the per-sample bar as mut/Mb when a usable panel size is
    # given. Below the reliable minimum, fall back to a plain count and warn.
    panel_mb = req.panel_size_mb
    if panel_mb is not None and panel_mb < MIN_TMB_PANEL_MB:
        warnings.append(
            f"Panel size {panel_mb:g} Mb is below the reliable minimum "
            f"({MIN_TMB_PANEL_MB} Mb) for TMB; showing mutation count instead."
        )
        panel_mb = None

    # Render
    if matrix is not None:
        fig = draw_oncoplot(
            matrix=matrix,
            mutation_colors=mutation_colors,
            mutation_burden=mutation_burden,
            panel_size_mb=panel_mb,
            clinical_data=clinical_df,
            clinical_cols=annot_cols,
            clinical_types=req.annotation_types,
            clinical_colors=req.annotation_colors,
            track_options=track_opts,
            display_names=req.display_names,
            group_boundaries=group_boundaries,
            show_tmb=req.show_tmb,
            show_gene_freq=req.show_gene_freq,
            show_sample_labels=req.show_sample_labels,
            annotations_position=req.annotations_position,
            title=req.title,
            fig_width=req.fig_width,
            fontsize=req.fontsize,
        )
    else:
        if not annot_cols:
            raise ValueError(
                "Assign at least one Annotation Track in annotation-only mode."
            )
        fig = draw_annotation_plot(
            samples=sorted_samples,
            clinical_data=clinical_df,
            clinical_cols=annot_cols,
            clinical_types=req.annotation_types,
            clinical_colors=req.annotation_colors,
            track_options=track_opts,
            display_names=req.display_names,
            group_boundaries=group_boundaries,
            show_sample_labels=req.show_sample_labels,
            annotations_position=req.annotations_position,
            title=req.title,
            fig_width=req.fig_width,
            fontsize=req.fontsize,
        )

    return fig, matrix, warnings


def render_plot(session: SessionData, req: RenderRequest) -> list[str]:
    """Render the interactive preview and cache it in the session.

    Only the lightweight low-DPI preview PNG (and the cheap CSV) are produced
    here so the auto-render loop stays responsive. The print-quality PNG and the
    PDF are deferred to :func:`render_export`, built on demand at download time.

    Returns a list of warning messages.
    """
    # Check cache
    h = _config_hash(req)
    if session.render_config_hash == h and session.cached_png is not None:
        return session.cached_warnings

    fig, matrix, warnings = _build_figure(session, req)

    buf_png = BytesIO()
    fig.savefig(buf_png, format="png", dpi=PREVIEW_DPI)
    session.cached_png = buf_png.getvalue()
    plt.close(fig)

    if matrix is not None:
        csv_buf = BytesIO()
        matrix.to_csv(csv_buf)
        session.cached_csv = csv_buf.getvalue()
    else:
        session.cached_csv = None

    # Invalidate the lazy exports; they are rebuilt from render_req on demand.
    session.cached_png_hires = None
    session.cached_pdf = None
    session.render_req = req
    session.cached_warnings = warnings
    session.render_config_hash = h
    return warnings


def render_export(session: SessionData, fmt: str) -> bytes | None:
    """Return the print-quality export for *fmt* (``"png"`` or ``"pdf"``).

    Built lazily from the last render request and cached, so repeated downloads
    are free. Returns ``None`` if nothing has been rendered yet.
    """
    if fmt == "png" and session.cached_png_hires is not None:
        return session.cached_png_hires
    if fmt == "pdf" and session.cached_pdf is not None:
        return session.cached_pdf
    if session.render_req is None:
        return None

    fig, _matrix, _warnings = _build_figure(session, session.render_req)
    buf = BytesIO()
    if fmt == "pdf":
        fig.savefig(buf, format="pdf", bbox_inches="tight")
        session.cached_pdf = buf.getvalue()
        out = session.cached_pdf
    else:
        fig.savefig(buf, format="png", dpi=EXPORT_DPI, bbox_inches="tight")
        session.cached_png_hires = buf.getvalue()
        out = session.cached_png_hires
    plt.close(fig)
    return out
