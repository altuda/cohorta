export interface UploadResponse {
  session_id: string;
  file_name: string;
  row_count: number;
  col_count: number;
  columns: string[];
  preview: Record<string, unknown>[];
  auto_roles: Record<string, string>;
}

export interface ColumnInfo {
  name: string;
  dtype: string;
  n_unique: number;
  unique_values: string[] | null;
}

export interface RolesResponse {
  roles: Record<string, string>;
  validation_errors: string[];
  mutation_types: string[] | null;
  annotation_unique_values: Record<string, string[]>;
}

export interface PaletteListResponse {
  categorical: string[];
  continuous: string[];
}

export interface PaletteColorsResponse {
  colors: string[];
}

export interface TrackOptionsPayload {
  show_values: boolean;
  text_color: string;
  tile_color: string | null;
}

export interface RenderRequest {
  roles: Record<string, string>;
  display_names: Record<string, string>;
  annotation_order: string[];
  annotation_types: Record<string, string>;
  annotation_colors: Record<string, Record<string, string> | string>;
  track_options: Record<string, TrackOptionsPayload>;
  mutation_colors: Record<string, string>;
  group_columns: string[];
  group_order: Record<string, string[]>;
  group_sort: Record<string, "asc" | "desc">;
  top_n_genes: number;
  show_tmb: boolean;
  panel_size_mb: number | null;
  show_gene_freq: boolean;
  show_sample_labels: boolean;
  annotations_position: string;
  title: string | null;
  fig_width: number;
  fontsize: number;
}

export interface RenderResponse {
  png_url: string;
  png_download_url: string;
  pdf_url: string | null;
  csv_url: string | null;
  warnings: string[];
}

export const COLUMN_ROLES = [
  "Skip",
  "Sample ID",
  "Gene / Feature",
  "Mutation Type",
  "Annotation Track",
] as const;

export type ColumnRole = (typeof COLUMN_ROLES)[number];
