"""FastAPI application for Oncoplot Builder."""

import sys
from pathlib import Path

# Ensure oncoplot_core is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers import upload, columns, palette, render

app = FastAPI(title="Oncoplot Builder API")

# CORS for development (Vite on port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(upload.router, prefix="/api")
app.include_router(columns.router, prefix="/api")
app.include_router(palette.router, prefix="/api")
app.include_router(render.router, prefix="/api")

# Production: serve React build
_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="spa")
