"""Render service: orchestrates oncoplot_core calls."""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
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
    DEFAULT_MUT_COLORS,
)

from ..session_store import SessionData
from ..models import RenderRequest


def _config_hash(req: RenderRequest) -> str:
    raw = req.model_dump_json(exclude_none=False)
    return hashlib.md5(raw.encode()).hexdigest()


def render_plot(session: SessionData, req: RenderRequest) -> list[str]:
    """Render the plot and cache PNG/PDF/CSV in session.

    Returns a list of warning messages.
    """
    # Check cache
    h = _config_hash(req)
    if session.render_config_hash == h and session.cached_png is not None:
        return []

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
    drow_cols = [c for c, r in roles.items() if r == "Data Row"]

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

        sample_data = clean.drop_duplicates(subset=[sample_col]).set_index(sample_col)
    else:
        matrix = None
        sample_data = df.drop_duplicates(subset=[sample_col]).set_index(sample_col)

    # Group-by
    group_series_list = []
    for gc in req.group_columns:
        if gc in sample_data.columns:
            group_series_list.append(sample_data[gc])

    sorted_samples, group_boundaries = sort_samples(
        matrix, group_series_list if group_series_list else None,
    )
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
            dr_dict[drc] = pd.to_numeric(sample_data[drc], errors="coerce")

    # Track options: convert from Pydantic to plain dict
    track_opts = {
        col: {
            "show_values": opts.show_values,
            "text_color": opts.text_color,
            "tile_color": opts.tile_color,
        }
        for col, opts in req.track_options.items()
    }

    # Mutation colors: apply defaults for missing types
    mutation_colors = dict(req.mutation_colors)
    if matrix is not None:
        all_types = sorted(
            [t for t in matrix.stack().unique() if pd.notna(t)],
            key=str,
        )
        for mt in all_types:
            if mt not in mutation_colors:
                mutation_colors[mt] = DEFAULT_MUT_COLORS.get(mt, "#808080")

    # Render
    if matrix is not None:
        fig = draw_oncoplot(
            matrix=matrix,
            mutation_colors=mutation_colors,
            clinical_data=clinical_df,
            clinical_cols=annot_cols,
            clinical_types=req.annotation_types,
            clinical_colors=req.annotation_colors,
            track_options=track_opts,
            data_rows=dr_dict,
            data_row_cmaps=req.data_row_cmaps,
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
        if not annot_cols and not drow_cols:
            raise ValueError(
                "Assign at least one Annotation Track or Data Row in annotation-only mode."
            )
        fig = draw_annotation_plot(
            samples=sorted_samples,
            clinical_data=clinical_df,
            clinical_cols=annot_cols,
            clinical_types=req.annotation_types,
            clinical_colors=req.annotation_colors,
            track_options=track_opts,
            data_rows=dr_dict,
            data_row_cmaps=req.data_row_cmaps,
            display_names=req.display_names,
            group_boundaries=group_boundaries,
            show_sample_labels=req.show_sample_labels,
            title=req.title,
            fig_width=req.fig_width,
            fontsize=req.fontsize,
        )

    # Export to buffers
    buf_png = BytesIO()
    fig.savefig(buf_png, format="png", dpi=300, bbox_inches="tight")
    session.cached_png = buf_png.getvalue()

    buf_pdf = BytesIO()
    fig.savefig(buf_pdf, format="pdf", bbox_inches="tight")
    session.cached_pdf = buf_pdf.getvalue()

    if matrix is not None:
        csv_buf = BytesIO()
        matrix.to_csv(csv_buf)
        session.cached_csv = csv_buf.getvalue()
    else:
        session.cached_csv = None

    plt.close(fig)

    session.render_config_hash = h
    return warnings
