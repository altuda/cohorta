import { create } from "zustand";
import type {
  UploadResponse,
  RenderRequest,
  TrackOptionsPayload,
} from "../types";

interface SessionState {
  // Session
  sessionId: string | null;
  fileName: string | null;
  rowCount: number;
  colCount: number;
  columns: string[];
  preview: Record<string, unknown>[];

  // Roles
  roles: Record<string, string>;
  displayNames: Record<string, string>;

  // Annotation tracks
  annotationOrder: string[];
  annotationTypes: Record<string, string>;
  annotationColors: Record<string, Record<string, string> | string>;
  trackOptions: Record<string, TrackOptionsPayload>;

  // Data rows
  dataRowCmaps: Record<string, string>;

  // Mutation colors
  mutationTypes: string[];
  annotationUniqueValues: Record<string, string[]>;
  mutationColors: Record<string, string>;

  // Grouping
  groupColumns: string[];

  // Plot settings
  topNGenes: number;
  showTmb: boolean;
  showGeneFreq: boolean;
  showSampleLabels: boolean;
  annotationsPosition: string;
  title: string | null;
  figWidth: number;
  fontsize: number;

  // Render state
  renderVersion: number;
  pngUrl: string | null;
  pdfUrl: string | null;
  csvUrl: string | null;

  // Actions
  setUploadResult: (res: UploadResponse) => void;
  setRole: (col: string, role: string) => void;
  setDisplayName: (col: string, name: string) => void;
  setAnnotationOrder: (order: string[]) => void;
  setAnnotationType: (col: string, type: string) => void;
  setAnnotationColor: (
    col: string,
    color: Record<string, string> | string
  ) => void;
  setTrackOption: (col: string, opts: Partial<TrackOptionsPayload>) => void;
  setDataRowCmap: (col: string, cmap: string) => void;
  setMutationTypes: (types: string[]) => void;
  setAnnotationUniqueValues: (vals: Record<string, string[]>) => void;
  setMutationColor: (type: string, color: string) => void;
  setMutationColorsBatch: (colors: Record<string, string>) => void;
  setGroupColumns: (cols: string[]) => void;
  setPlotSetting: <K extends keyof SessionState>(
    key: K,
    value: SessionState[K]
  ) => void;
  setRenderResult: (
    pngUrl: string,
    pdfUrl: string | null,
    csvUrl: string | null
  ) => void;
  buildRenderRequest: () => RenderRequest;
  reset: () => void;
}

const initialState = {
  sessionId: null,
  fileName: null,
  rowCount: 0,
  colCount: 0,
  columns: [],
  preview: [],
  roles: {},
  displayNames: {},
  annotationOrder: [],
  annotationTypes: {},
  annotationColors: {},
  trackOptions: {},
  dataRowCmaps: {},
  mutationTypes: [],
  annotationUniqueValues: {},
  mutationColors: {},
  groupColumns: [],
  topNGenes: 20,
  showTmb: false,
  showGeneFreq: false,
  showSampleLabels: false,
  annotationsPosition: "bottom",
  title: "Oncoplot" as string | null,
  figWidth: 14,
  fontsize: 8,
  renderVersion: 0,
  pngUrl: null,
  pdfUrl: null,
  csvUrl: null,
};

export const useSessionStore = create<SessionState>((set, get) => ({
  ...initialState,

  setUploadResult: (res) =>
    set({
      sessionId: res.session_id,
      fileName: res.file_name,
      rowCount: res.row_count,
      colCount: res.col_count,
      columns: res.columns,
      preview: res.preview,
      roles: res.auto_roles,
      displayNames: Object.fromEntries(res.columns.map((c) => [c, c])),
      // Reset everything else
      annotationOrder: [],
      annotationTypes: {},
      annotationColors: {},
      trackOptions: {},
      dataRowCmaps: {},
      mutationTypes: [],
      annotationUniqueValues: {},
      mutationColors: {},
      groupColumns: [],
      pngUrl: null,
      pdfUrl: null,
      csvUrl: null,
      renderVersion: 0,
    }),

  setRole: (col, role) =>
    set((s) => {
      const roles = { ...s.roles, [col]: role };
      // Recompute annotation order
      const annotCols = Object.entries(roles)
        .filter(([, r]) => r === "Annotation Track")
        .map(([c]) => c);
      const annotationOrder = s.annotationOrder.filter((c) =>
        annotCols.includes(c)
      );
      for (const c of annotCols) {
        if (!annotationOrder.includes(c)) annotationOrder.push(c);
      }
      return { roles, annotationOrder };
    }),

  setDisplayName: (col, name) =>
    set((s) => ({ displayNames: { ...s.displayNames, [col]: name } })),

  setAnnotationOrder: (order) => set({ annotationOrder: order }),

  setAnnotationType: (col, type) =>
    set((s) => ({ annotationTypes: { ...s.annotationTypes, [col]: type } })),

  setAnnotationColor: (col, color) =>
    set((s) => ({
      annotationColors: { ...s.annotationColors, [col]: color },
    })),

  setTrackOption: (col, opts) =>
    set((s) => {
      const existing = s.trackOptions[col] ?? {
        show_values: false,
        text_color: "#000000",
        tile_color: null,
      };
      return {
        trackOptions: {
          ...s.trackOptions,
          [col]: { ...existing, ...opts },
        },
      };
    }),

  setDataRowCmap: (col, cmap) =>
    set((s) => ({ dataRowCmaps: { ...s.dataRowCmaps, [col]: cmap } })),

  setMutationTypes: (types) => set({ mutationTypes: types }),

  setAnnotationUniqueValues: (vals) => set({ annotationUniqueValues: vals }),

  setMutationColor: (type, color) =>
    set((s) => ({ mutationColors: { ...s.mutationColors, [type]: color } })),

  setMutationColorsBatch: (colors) =>
    set((s) => ({ mutationColors: { ...s.mutationColors, ...colors } })),

  setGroupColumns: (cols) => set({ groupColumns: cols }),

  setPlotSetting: (key, value) => set({ [key]: value } as Partial<SessionState>),

  setRenderResult: (pngUrl, pdfUrl, csvUrl) =>
    set((s) => ({
      pngUrl,
      pdfUrl,
      csvUrl,
      renderVersion: s.renderVersion + 1,
    })),

  buildRenderRequest: (): RenderRequest => {
    const s = get();
    return {
      roles: s.roles,
      display_names: s.displayNames,
      annotation_order: s.annotationOrder,
      annotation_types: s.annotationTypes,
      annotation_colors: s.annotationColors,
      track_options: s.trackOptions,
      data_row_cmaps: s.dataRowCmaps,
      mutation_colors: s.mutationColors,
      group_columns: s.groupColumns,
      top_n_genes: s.topNGenes,
      show_tmb: s.showTmb,
      show_gene_freq: s.showGeneFreq,
      show_sample_labels: s.showSampleLabels,
      annotations_position: s.annotationsPosition,
      title: s.title,
      fig_width: s.figWidth,
      fontsize: s.fontsize,
    };
  },

  reset: () => set(initialState),
}));
