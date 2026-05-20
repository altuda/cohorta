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
from collections import OrderedDict
from io import BytesIO

from oncoplot_core import (
    COLUMN_ROLES, DEFAULT_MUT_COLORS,
    CONTINUOUS_CMAPS, CATEGORICAL_PALETTES,
    _get_cmap, _palette_colors, _auto_assign_roles,
    build_mutation_matrix, sort_samples,
    draw_oncoplot, draw_annotation_plot,
)

# ────────────────────────────────────────────────────────────────
# Page configuration
# ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Oncoplot Builder", layout="wide", page_icon="\U0001f9ec",
)


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
    track_options = {}
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

    # ── Annotation track ordering (consolidated) ────────────────
    _all_annot = [c for c, r in col_roles.items() if r == "Annotation Track"]
    if len(_all_annot) > 1:
        with st.sidebar.expander("Track order", expanded=True):
            _remaining = list(_all_annot)
            _ordered = []
            for _pos in range(len(_all_annot)):
                _label = col_display.get(_remaining[0], _remaining[0]) if _remaining else ""
                _pick = st.selectbox(
                    f"Position {_pos + 1}",
                    _remaining,
                    format_func=lambda c: col_display.get(c, c),
                    key=f"ao_pos_{_pos}",
                )
                _ordered.append(_pick)
                _remaining = [c for c in _remaining if c not in _ordered]
            _all_annot = _ordered

    # ── Derive logical columns ─────────────────────────────────
    sample_cols = [c for c, r in col_roles.items() if r == "Sample ID"]
    gene_cols = [c for c, r in col_roles.items() if r == "Gene / Feature"]
    mut_cols = [c for c, r in col_roles.items() if r == "Mutation Type"]
    annot_cols = _all_annot
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
        show_tmb = st.sidebar.checkbox("Show Mutation Burden bar", False)
        show_gene_freq = st.sidebar.checkbox("Show Gene Frequency bar", False)
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
