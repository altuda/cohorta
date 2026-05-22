"""Shared constants for the Oncoplot Builder."""

COLUMN_ROLES = [
    "Skip",
    "Sample ID",
    "Gene / Feature",
    "Mutation Type",
    "Annotation Track",
]

DEFAULT_MUT_COLORS = {
    "Missense_Mutation":      "#26A269",
    "Nonsense_Mutation":      "#E01B24",
    "Frame_Shift_Del":        "#1A5FB4",
    "Frame_Shift_Ins":        "#613583",
    "Splice_Site":            "#E66100",
    "In_Frame_Del":           "#A51D2D",
    "In_Frame_Ins":           "#C64600",
    "Translation_Start_Site": "#63452C",
    "Nonstop_Mutation":       "#F5C211",
    "Multi_Hit":              "#333333",
}

FALLBACK_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
]

BG_COLOR = "#E8E8E8"

CONTINUOUS_CMAPS = [
    "viridis", "plasma", "inferno", "magma",
    "coolwarm", "RdBu", "YlOrRd", "Blues",
]
CATEGORICAL_PALETTES = [
    "tab10", "Set1", "Set2", "Set3",
    "Pastel1", "Pastel2", "Accent", "Dark2",
]

_SAMPLE_HINTS = [
    "sampleid", "sample_id", "patientid", "patient_id",
    "tumor_sample", "case_id", "subject_id", "barcode", "sample",
]
_GENE_HINTS = [
    "hugo_symbol", "hugo", "gene_name", "gene_symbol",
    "alteration", "feature", "gene",
]
_MUT_HINTS = [
    "variant_classification", "variant_class", "mutation_type",
    "mut_type", "variant_type", "consequence", "vep_consequence",
]
