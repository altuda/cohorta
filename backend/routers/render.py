"""Render endpoint: generate oncoplot and serve cached output."""

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import Response

from ..session_store import store
from ..models import RenderRequest, RenderResponse
from ..services.render_service import render_plot

router = APIRouter()


def _get_session(session_id: str):
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    return session


@router.post("/render", response_model=RenderResponse)
async def render(body: RenderRequest, x_session_id: str = Header()):
    session = _get_session(x_session_id)
    try:
        warnings = render_plot(session, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    sid = session.session_id
    return RenderResponse(
        png_url=f"/api/render/{sid}/png",
        pdf_url=f"/api/render/{sid}/pdf",
        csv_url=f"/api/render/{sid}/csv" if session.cached_csv is not None else None,
        warnings=warnings,
    )


@router.get("/render/{session_id}/png")
async def get_png(session_id: str):
    session = _get_session(session_id)
    if session.cached_png is None:
        raise HTTPException(status_code=404, detail="No render available. Generate first.")
    return Response(
        content=session.cached_png,
        media_type="image/png",
        headers={"Content-Disposition": "inline; filename=oncoplot.png"},
    )


@router.get("/render/{session_id}/pdf")
async def get_pdf(session_id: str):
    session = _get_session(session_id)
    if session.cached_pdf is None:
        raise HTTPException(status_code=404, detail="No render available. Generate first.")
    return Response(
        content=session.cached_pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=oncoplot.pdf"},
    )


@router.get("/render/{session_id}/csv")
async def get_csv(session_id: str):
    session = _get_session(session_id)
    if session.cached_csv is None:
        raise HTTPException(status_code=404, detail="No CSV available (annotation-only mode).")
    return Response(
        content=session.cached_csv,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mutation_matrix.csv"},
    )
