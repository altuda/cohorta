"""Data processing: mutation matrix construction and sample sorting."""

import numpy as np
import pandas as pd


def build_mutation_matrix(df, sample_col, gene_col, mut_col):
    """Build gene x sample mutation matrix from long-format data.

    When *mut_col* is ``None`` each cell value is the gene name so that
    every gene/alteration can receive its own colour.
    """
    if mut_col is None:
        dedup = df.drop_duplicates(subset=[gene_col, sample_col]).copy()
        dedup["_mut"] = dedup[gene_col]
        matrix = dedup.pivot(index=gene_col, columns=sample_col, values="_mut")
    else:
        n_types = (
            df.groupby([gene_col, sample_col])[mut_col]
            .nunique()
            .reset_index(name="_n")
        )
        first_mut = (
            df.groupby([gene_col, sample_col])[mut_col]
            .first()
            .reset_index()
        )
        merged = first_mut.merge(n_types, on=[gene_col, sample_col])
        merged.loc[merged["_n"] > 1, mut_col] = "Multi_Hit"
        matrix = merged.pivot(index=gene_col, columns=sample_col, values=mut_col)

    freq = matrix.notna().sum(axis=1).sort_values(ascending=False)
    return matrix.loc[freq.index]


def sort_samples(matrix, group_series_list=None, group_orders=None,
                 group_sort_modes=None):
    """Waterfall-sort samples with optional multi-level hierarchical grouping.

    Parameters
    ----------
    matrix : DataFrame or None
        Gene x sample mutation matrix.  ``None`` in annotation-only mode.
    group_series_list : list[Series] or None
        Ordered list of grouping Series (level 0 = outermost).
    group_orders : list[list[str]] or None
        Per-level custom block order (aligned to ``group_series_list``); each
        entry is an explicit ordering of that level's group values, or ``None``
        to keep the default mutation-burden order.  Values absent from a custom
        list are appended after the listed ones, in burden order.
    group_sort_modes : list[str] or None
        Per-level numeric sort mode (aligned to ``group_series_list``): one of
        ``"asc"``, ``"desc"`` or ``None``.  When set, that level orders the
        samples in its scope by the column's numeric value instead of splitting
        them into one block per distinct value.  Such a level draws no group
        boundaries and acts as the terminal sort for its branch.

    Returns
    -------
    sorted_samples : list[str]
    group_boundaries : dict[int, list[tuple[str, int, int]]]
        Keys are level indices.  Values are lists of
        ``(display_label, start_col, end_col)``.
    """
    if matrix is not None:
        binary = matrix.notna().astype(int).T
        sort_cols = list(binary.columns)
        all_samples = binary.index.tolist()
    else:
        binary = None
        sort_cols = []
        all_samples = []
        if group_series_list:
            idx = group_series_list[0].index
            for gs in group_series_list[1:]:
                idx = idx.union(gs.index)
            all_samples = idx.tolist()

    if not group_series_list:
        if binary is not None:
            idx = binary.sort_values(by=sort_cols, ascending=False).index.tolist()
        else:
            idx = all_samples
        return idx, {}

    def _sort_recursive(sample_list, level):
        """Sort *sample_list* by group at *level*, recurse into inner levels."""
        if level >= len(group_series_list):
            if binary is not None and sample_list:
                sub = binary.loc[binary.index.intersection(sample_list)]
                return sub.sort_values(
                    by=sort_cols, ascending=False,
                ).index.tolist()
            return list(sample_list)

        gs = group_series_list[level]
        groups = gs.reindex(sample_list)

        unique_groups = list(groups.dropna().unique())
        if binary is not None:
            def _burden(g):
                m = groups[groups == g].index.intersection(binary.index)
                return -int(binary.loc[m].values.sum()) if len(m) else 0
            unique_groups.sort(key=_burden)
        else:
            unique_groups.sort(key=lambda g: -int((groups == g).sum()))

        ordered = []
        boundaries_at_level = []

        for g in unique_groups:
            members = groups[groups == g].index.tolist()
            if not members:
                continue
            sub_sorted = _sort_recursive(members, level + 1)
            boundaries_at_level.append(
                (str(g), len(ordered), len(ordered) + len(sub_sorted)),
            )
            ordered.extend(sub_sorted)

        rest = [s for s in sample_list if s not in set(ordered)]
        if rest:
            sub_sorted = _sort_recursive(rest, level + 1)
            boundaries_at_level.append(
                ("Other", len(ordered), len(ordered) + len(sub_sorted)),
            )
            ordered.extend(sub_sorted)

        return ordered, boundaries_at_level

    def _sort_mode(level):
        """Return 'asc'/'desc' if this level is a numeric sort, else None."""
        if group_sort_modes and level < len(group_sort_modes):
            m = group_sort_modes[level]
            if m in ("asc", "desc"):
                return m
        return None

    # Pre-compute a global sort rank for every level so that inner
    # groups keep the same order across all parent groups.
    _global_rank = {}
    for _lvl, _gs in enumerate(group_series_list):
        if _sort_mode(_lvl):
            continue  # numeric-sort levels produce no blocks/ranks
        _uvals = list(_gs.dropna().unique())
        if binary is not None:
            def _global_burden(g, _s=_gs):
                m = _s[_s == g].index.intersection(binary.index)
                return -int(binary.loc[m].values.sum()) if len(m) else 0
            _uvals.sort(key=_global_burden)
        else:
            def _global_count(g, _s=_gs):
                return -int((_s == g).sum())
            _uvals.sort(key=_global_count)
        # Apply a user-defined block order on top of the burden order. The sort
        # is stable, so any values not named in the custom list keep their
        # burden ranking and trail the explicitly ordered ones. Group values may
        # be numeric, so match against the string form the frontend sends.
        _custom = (
            group_orders[_lvl]
            if group_orders and _lvl < len(group_orders)
            else None
        )
        if _custom:
            _pos = {str(v): i for i, v in enumerate(_custom)}
            _uvals.sort(key=lambda g, _p=_pos, _n=len(_custom): _p.get(str(g), _n))
        _global_rank[_lvl] = {g: i for i, g in enumerate(_uvals)}

    all_boundaries = {}

    def _collect(sample_list, level, global_offset):
        """Sort and collect boundaries at all levels."""
        if level >= len(group_series_list):
            if binary is not None and sample_list:
                sub = binary.loc[binary.index.intersection(sample_list)]
                return sub.sort_values(
                    by=sort_cols, ascending=False,
                ).index.tolist()
            return list(sample_list)

        mode = _sort_mode(level)
        if mode:
            # Numeric ordering: sort this scope by the column's value and stop.
            # No per-value blocks and no boundaries are emitted for this level.
            gs = group_series_list[level]
            vals = pd.to_numeric(gs.reindex(sample_list), errors="coerce")
            return vals.sort_values(
                ascending=(mode == "asc"), kind="stable", na_position="last",
            ).index.tolist()

        gs = group_series_list[level]
        groups = gs.reindex(sample_list)
        unique_groups = list(groups.dropna().unique())

        rank = _global_rank.get(level, {})
        unique_groups.sort(key=lambda g: rank.get(g, 999))

        ordered = []
        local_offset = 0

        for g in unique_groups:
            members = groups[groups == g].index.tolist()
            if not members:
                continue
            sub_sorted = _collect(members, level + 1, global_offset + local_offset)
            all_boundaries.setdefault(level, []).append(
                (str(g), global_offset + local_offset,
                 global_offset + local_offset + len(sub_sorted))
            )
            ordered.extend(sub_sorted)
            local_offset += len(sub_sorted)

        rest = [s for s in sample_list if s not in set(ordered)]
        if rest:
            sub_sorted = _collect(rest, level + 1, global_offset + local_offset)
            all_boundaries.setdefault(level, []).append(
                ("Other", global_offset + local_offset,
                 global_offset + local_offset + len(sub_sorted))
            )
            ordered.extend(sub_sorted)

        return ordered

    sorted_samples = _collect(all_samples, 0, 0)
    return sorted_samples, all_boundaries
