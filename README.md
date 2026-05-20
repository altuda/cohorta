# Oncoplot Builder

A Streamlit web application for creating publication-quality co-mutation (oncoplot) figures from Excel datasets.

## Features

- **Interactive column mapping** — auto-detects Sample ID, Gene, and Mutation Type columns; manually assign Annotation Tracks and Data Rows
- **Mutation matrix** — waterfall-sorted heatmap with per-gene or per-mutation-type colouring
- **TMB bar** — stacked Tumour Mutation Burden bar chart above the matrix
- **Gene frequency bar** — horizontal bar coloured by dominant mutation type per gene
- **Annotation tracks** — categorical (colour-mapped) or continuous (heatmap + colour bar) clinical tracks, positionable above or below the matrix
- **Data rows** — continuous numeric heatmaps with configurable colormaps
- **Sample grouping** — group and sort samples by any column, with visual separators and labels
- **Colour customisation**
  - Palette selector (tab10, Set1, Set2, etc.) for gene/mutation colours
  - Per-value colour pickers for fine-tuning
  - "Use single colour" mode for presence/absence plots
  - Per-track palette and colour picker controls for annotation tracks
- **Sample labels** — toggleable, automatically placed on the opposite side from annotations to avoid overlap
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
  app.py                 # Main Streamlit application
  requirements.txt       # Python dependencies
  sample_mutations.xlsx  # Example dataset
  README.md
```

## License

This project is provided as-is for research and educational use.
