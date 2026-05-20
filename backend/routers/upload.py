"""Upload endpoint: parse .xlsx and create session."""

from fastapi import APIRouter, UploadFile, File, HTTPException
import pandas as pd

from ..session_store import store
from ..models import UploadResponse

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from oncoplot_core import _auto_assign_roles

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are accepted.")

    try:
        df = pd.read_excel(file.file, engine="openpyxl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse Excel file: {e}")

    if df.empty:
        raise HTTPException(status_code=400, detail="The uploaded file contains no data.")

    auto_roles = _auto_assign_roles(df.columns.tolist())
    session = store.create(df, file.filename, auto_roles)

    # Build preview (first 5 rows), converting NaN/NaT to None for JSON
    preview = df.head(5).where(df.head(5).notna(), None).to_dict(orient="records")

    return UploadResponse(
        session_id=session.session_id,
        file_name=session.file_name,
        row_count=len(df),
        col_count=len(df.columns),
        columns=session.columns,
        preview=preview,
        auto_roles=session.auto_roles,
    )
