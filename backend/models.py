"""Pydantic request/response models."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel


# ── Upload ───────────────────────────────────────────────────────
class UploadResponse(BaseModel):
    session_id: str
    file_name: str
    row_count: int
    col_count: int
    columns: list[str]
    preview: list[dict[str, Any]]
    auto_roles: dict[str, str]


# ── Columns ──────────────────────────────────────────────────────
class ColumnInfo(BaseModel):
    name: str
    dtype: str
    n_unique: int
    unique_values: list[str] | None  # None if >50 unique


class ColumnsResponse(BaseModel):
    columns: list[ColumnInfo]


class RolesRequest(BaseModel):
    roles: dict[str, str]


class RolesResponse(BaseModel):
    roles: dict[str, str]
    validation_errors: list[str]
    mutation_types: list[str] | None
    annotation_unique_values: dict[str, list[str]]


# ── Palette ──────────────────────────────────────────────────────
class PaletteListResponse(BaseModel):
    categorical: list[str]
    continuous: list[str]


class PaletteColorsRequest(BaseModel):
    palette_name: str
    n_colors: int


class PaletteColorsResponse(BaseModel):
    colors: list[str]


# ── Render ───────────────────────────────────────────────────────
class TrackOptionsPayload(BaseModel):
    show_values: bool = False
    text_color: str = "#000000"
    tile_color: str | None = None
    # For numeric (Continuous) tracks: render the values as an x/y chart instead
    # of a colour strip. None → colour strip (default); otherwise one of
    # "columns" | "points" | "lollipop" | "connected".
    value_plot: str | None = None
    plot_color: str = "#4C72B0"
    # Size multiplier for the value chart, interpreted per style: point/marker
    # size, line width, lollipop head, or bar width. 1.0 = default.
    plot_size: float = 1.0
    # Per-track placement relative to the matrix: "top" | "bottom". None →
    # follow the global annotations_position.
    position: str | None = None


class RenderRequest(BaseModel):
    roles: dict[str, str]
    display_names: dict[str, str] = {}
    annotation_order: list[str] = []
    annotation_types: dict[str, str] = {}
    annotation_colors: dict[str, Any] = {}
    track_options: dict[str, TrackOptionsPayload] = {}
    mutation_colors: dict[str, str] = {}
    group_columns: list[str] = []
    # Custom left-to-right order of group blocks, keyed by grouping column name:
    # {column: [value, ...]}. Values not listed fall back to mutation-burden order.
    group_order: dict[str, list[str]] = {}
    # Numeric ordering for a grouping column, keyed by name: {column: "asc"|"desc"}.
    # When set, that level orders samples by the numeric value instead of producing
    # one block per distinct value (e.g. order by age rather than grouping on it).
    group_sort: dict[str, str] = {}
    top_n_genes: int = 20
    show_tmb: bool = False
    # Panel/exome size in megabases. When provided (and >= the minimum reliable
    # size), the per-sample mutation bar is shown as true TMB in mut/Mb instead
    # of a raw count. None → show the honest mutation count.
    panel_size_mb: float | None = None
    show_gene_freq: bool = False
    show_sample_labels: bool = False
    annotations_position: str = "bottom"
    title: str | None = "Oncoplot"
    fig_width: int = 14
    fontsize: int = 8


class RenderResponse(BaseModel):
    png_url: str               # low-DPI on-screen preview
    png_download_url: str      # 300-DPI PNG, built lazily on download
    pdf_url: str | None
    csv_url: str | None
    warnings: list[str]
