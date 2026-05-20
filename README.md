# Oncoplot Builder

A Streamlit web application for creating publication-quality co-mutation (oncoplot) figures from Excel datasets.

## Features

- **Interactive column mapping** — auto-detects Sample ID, Gene, and Mutation Type columns; manually assign Annotation Tracks and Data Rows
- **Annotation-only mode** — leave Gene / Feature unassigned to render just annotation tracks and data rows without a mutation matrix
- **Mutation matrix** — waterfall-sorted heatmap with per-gene or per-mutation-type colouring
- **TMB bar** — stacked Tumour Mutation Burden bar chart above the matrix
- **Gene frequency bar** — horizontal bar coloured by dominant mutation type per gene
- **Annotation tracks** — categorical (colour-mapped) or continuous (heatmap + colour bar) clinical tracks, positionable above or below the matrix
- **Data rows** — continuous numeric heatmaps with configurable colormaps
- **Multi-level sample grouping** — up to 4 hierarchical grouping levels with visual separators and stacked labels; consistent inner-group ordering across parent groups
- **Annotation track ordering** — reorder tracks via display-order controls
- **Colour customisation**
  - Palette selector (tab10, Set1, Set2, etc.) for gene/mutation colours
  - Visual numbered colour swatches with horizontal radio selectors per category value
  - Custom colour picker fallback per value
  - "Use single tile colour" mode per track (hides palette and legend entries)
  - Evenly-spaced default colour spread across the palette for better variety with few categories
- **Tile values** — optionally display values as text inside annotation tiles with configurable text colour
- **Sample labels** — toggleable, automatically placed on the opposite side from annotations to avoid overlap
- **Title** — configurable plot title
- **Export** — download as PNG (300 dpi), PDF, or mutation matrix CSV

## Requirements

- Python 3.9+
- Dependencies listed in `requirements.txt`

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL shown in the terminal (typically `http://localhost:8501`).

## Usage

1. **Upload** an `.xlsx` file containing mutation data in long format (one row per sample-gene pair).
2. **Map columns** in the sidebar — assign roles: Sample ID, Gene / Feature, Mutation Type, Annotation Track, Data Row, or Skip.
3. **Configure plot settings** — choose top-N genes, toggle TMB/frequency bars, set annotation position (top/bottom), adjust figure width and font size.
4. **Customise colours** — expand the colour editors to pick palettes and tweak individual colours.
5. **Generate** — click the button to render the oncoplot.
6. **Download** — save the figure as PNG, PDF, or export the underlying matrix as CSV.

## Input format

The app expects an Excel file with at least two columns:

| Column | Description |
|---|---|
| **Sample ID** | Unique identifier per patient/sample |
| **Gene / Feature** | Gene name or alteration identifier |
| **Mutation Type** *(optional)* | e.g. Missense_Mutation, Frame_Shift_Del |
| **Annotation Track** *(optional)* | Clinical/categorical or continuous sample-level data |
| **Data Row** *(optional)* | Numeric sample-level data shown as a heatmap row |

A sample dataset (`sample_mutations.xlsx`) is included in the repository.

## Project structure

```
oncoplot/
  app.py                           # Streamlit entry point (UI only)
  requirements.txt                 # Python dependencies
  sample_mutations.xlsx            # Example dataset
  README.md
  oncoplot_core/                   # Plotting and data logic
    __init__.py                    # Re-exports public API
    constants.py                   # Colour palettes, role lists, defaults
    helpers.py                     # _get_cmap, _palette_colors, _auto_assign_roles
    data.py                        # build_mutation_matrix, sort_samples
    render_shared.py               # Shared rendering helpers (tracks, legends, separators)
    render_oncoplot.py             # draw_oncoplot (matrix + TMB + gene freq + tracks)
    render_annotation.py           # draw_annotation_plot (annotation-only mode)
```

## License

This project is provided as-is for research and educational use.
