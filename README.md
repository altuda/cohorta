# Oncoplot Builder

A React + FastAPI web application for creating publication-quality co-mutation (oncoplot) figures from Excel datasets.

## Features

- **Interactive column mapping** — auto-detects Sample ID, Gene, and Mutation Type columns; manually assign Annotation Tracks
- **Annotation-only mode** — leave Gene / Feature unassigned to render just annotation tracks without a mutation matrix
- **Mutation matrix** — waterfall-sorted heatmap with per-gene or per-mutation-type colouring
- **TMB bar** — stacked Tumour Mutation Burden bar chart above the matrix
- **Gene frequency bar** — horizontal bar coloured by dominant mutation type per gene
- **Annotation tracks** — categorical (colour-mapped) or continuous (heatmap + colour bar) clinical tracks, positionable above or below the matrix
- **Multi-level sample grouping** — up to 4 hierarchical grouping levels with visual separators and labels; drag to reorder group blocks
- **Drag-and-drop track ordering** — reorder annotation tracks visually via drag handles
- **Colour customisation**
  - Palette selector (tab10, Set1, Set2, etc.) for gene/mutation and annotation colours
  - Clickable palette swatches per category value for quick colour assignment
  - Full hex colour picker popover with manual hex input per value
  - "Use single colour" mode for mutation types; "single tile colour" mode per annotation track
  - Evenly-spaced default colour spread across the palette for better variety with few categories
- **Tile values** — optionally display values as text inside annotation tiles with configurable text colour
- **Sample labels** — toggleable, position switchable between top and bottom in both standard and annotation-only mode
- **Live preview** — debounced auto-render on config changes (toggleable)
- **Title** — configurable plot title, centred on the plot area
- **Export** — download as PNG (300 dpi), PDF, or mutation matrix CSV

## Requirements

- Python 3.9+
- Node.js 18+

## Quick start

```bash
# Backend
pip install -r backend/requirements.txt
uvicorn backend.main:app --port 8000 --reload

# Frontend (development)
cd frontend
npm install
npm run dev
```

For production, build the frontend and let FastAPI serve it:

```bash
cd frontend && npm run build
cd .. && uvicorn backend.main:app --port 8000
```

Then open `http://localhost:8000`.

## Usage

1. **Upload** an `.xlsx` file containing mutation data in long format (one row per sample-gene pair).
2. **Map columns** in the sidebar — assign roles: Sample ID, Gene / Feature, Mutation Type, Annotation Track, or Skip.
3. **Configure plot settings** — choose top-N genes, toggle TMB/frequency bars, set annotation/label position (top/bottom), adjust figure width and font size.
4. **Customise colours** — click colour swatches to pick from the palette, or open the colour picker for full control with hex input.
5. **Reorder tracks** — drag and drop annotation tracks in the sidebar to change their display order.
6. **Generate** — click the button or enable auto-render for live preview.
7. **Download** — save the figure as PNG, PDF, or export the underlying matrix as CSV.

## Input format

The app expects an Excel file with at least two columns:

| Column | Description |
|---|---|
| **Sample ID** | Unique identifier per patient/sample |
| **Gene / Feature** | Gene name or alteration identifier |
| **Mutation Type** *(optional)* | e.g. Missense_Mutation, Frame_Shift_Del |
| **Annotation Track** *(optional)* | Clinical/categorical or continuous sample-level data |

A sample dataset (`sample_mutations.xlsx`) is included in the repository.

## Project structure

```
oncoplot/
  sample_mutations.xlsx            # Example dataset
  README.md
  oncoplot_core/                   # Plotting and data logic (pure Python, no UI)
    __init__.py                    # Re-exports public API
    constants.py                   # Colour palettes, role lists, defaults
    helpers.py                     # _get_cmap, _palette_colors, _auto_assign_roles
    data.py                        # build_mutation_matrix, sort_samples
    render_shared.py               # Shared rendering helpers (tracks, legends, separators)
    render_oncoplot.py             # draw_oncoplot (matrix + mutation count + gene freq + tracks)
    render_annotation.py           # draw_annotation_plot (annotation-only mode)
  backend/
    main.py                        # FastAPI app, CORS, SPA static mount
    session_store.py               # In-memory session manager (30-min TTL)
    models.py                      # Pydantic request/response schemas
    requirements.txt               # Python dependencies
    routers/
      upload.py                    # POST /api/upload
      columns.py                   # GET /api/columns, POST /api/columns/roles
      palette.py                   # GET /api/palettes, POST /api/palette-colors
      render.py                    # POST /api/render, GET /api/render/{id}/png|pdf|csv
    services/
      render_service.py            # Orchestrates oncoplot_core calls
  frontend/
    package.json
    vite.config.ts                 # Proxy /api → localhost:8000 in dev
    tsconfig.json
    src/
      main.tsx
      App.tsx
      api/
        client.ts                  # Axios instance with session header
        hooks.ts                   # TanStack Query hooks
      types/
        index.ts                   # TypeScript interfaces
      stores/
        useSessionStore.ts         # Zustand store for all app state
      components/
        layout/
          AppShell.tsx             # Header + sidebar + main area + auto-render
          Sidebar.tsx              # Dynamic-width sidebar container
        upload/
          FileUploader.tsx         # Drag-and-drop upload zone
          DataPreview.tsx          # 5-row data preview table
        columns/
          ColumnRolePanel.tsx      # All column role cards
          ColumnRoleCard.tsx       # Single column role config
          AnnotationTrackOptions.tsx  # Categorical/continuous colour config
          TrackOrderPanel.tsx      # @dnd-kit drag-and-drop track reorder
        plot/
          PlotSettingsPanel.tsx    # Top-N, TMB, font size, etc.
          MutationColorsPanel.tsx  # Mutation type colour config
          GroupingPanel.tsx        # Multi-level grouping selector
        preview/
          PlotPreview.tsx          # <img> with loading skeleton
          DownloadBar.tsx          # PNG/PDF/CSV download buttons
        ErrorBoundary.tsx          # React error boundary
```

## Tech stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19 + TypeScript + Vite |
| Styling | Tailwind CSS |
| Drag-and-drop | @dnd-kit/sortable |
| Colour picker | react-colorful |
| HTTP / caching | Axios + TanStack Query v5 |
| State | Zustand |
| Backend | FastAPI + uvicorn |
| Plotting | matplotlib (via oncoplot_core) |

## License

This project is provided as-is for research and educational use.
