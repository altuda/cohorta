"""Column introspection and role validation endpoints."""

from fastapi import APIRouter, Header, HTTPException
import pandas as pd

from ..session_store import store
from ..models import ColumnsResponse, ColumnInfo, RolesRequest, RolesResponse

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from oncoplot_core import COLUMN_ROLES

router = APIRouter()


def _get_session(session_id: str):
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    return session


@router.get("/columns", response_model=ColumnsResponse)
async def get_columns(x_session_id: str = Header()):
    session = _get_session(x_session_id)
    df = session.df
    infos = []
    for col in df.columns:
        n_unique = int(df[col].nunique())
        unique_vals = (
            sorted(df[col].dropna().unique().astype(str).tolist())[:50]
            if n_unique <= 50
            else None
        )
        infos.append(ColumnInfo(
            name=col,
            dtype=str(df[col].dtype),
            n_unique=n_unique,
            unique_values=unique_vals,
        ))
    return ColumnsResponse(columns=infos)


@router.post("/columns/roles", response_model=RolesResponse)
async def set_roles(body: RolesRequest, x_session_id: str = Header()):
    session = _get_session(x_session_id)
    df = session.df
    roles = body.roles
    errors = []

    # Validate
    sample_cols = [c for c, r in roles.items() if r == "Sample ID"]
    gene_cols = [c for c, r in roles.items() if r == "Gene / Feature"]
    mut_cols = [c for c, r in roles.items() if r == "Mutation Type"]

    if len(sample_cols) != 1:
        errors.append("Assign exactly one column as Sample ID.")
    if len(gene_cols) > 1:
        errors.append("At most one column can be Gene / Feature.")
    if len(mut_cols) > 1:
        errors.append("At most one column can be Mutation Type.")
    if mut_cols and not gene_cols:
        errors.append("Mutation Type requires a Gene / Feature column.")

    # Extract mutation types
    mutation_types = None
    if gene_cols and not errors:
        gene_col = gene_cols[0]
        sample_col = sample_cols[0]
        if mut_cols:
            mut_col = mut_cols[0]
            data_mut_types = list(df[mut_col].dropna().unique())
            try:
                has_multi = (
                    df.groupby([gene_col, sample_col])[mut_col].nunique().max() > 1
                )
                if has_multi and "Multi_Hit" not in data_mut_types:
                    data_mut_types.append("Multi_Hit")
            except Exception:
                pass
            mutation_types = sorted(set(str(t) for t in data_mut_types))
        else:
            gene_freq = df[gene_col].value_counts()
            mutation_types = gene_freq.index.tolist()

    # Extract annotation unique values
    annot_cols = [c for c, r in roles.items() if r == "Annotation Track"]
    annotation_unique_values = {}
    for col in annot_cols:
        vals = sorted(df[col].dropna().unique().astype(str).tolist())[:50]
        annotation_unique_values[col] = vals

    return RolesResponse(
        roles=roles,
        validation_errors=errors,
        mutation_types=mutation_types,
        annotation_unique_values=annotation_unique_values,
    )
