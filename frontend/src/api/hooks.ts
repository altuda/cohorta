import { useMutation, useQuery } from "@tanstack/react-query";
import api, { setSessionId } from "./client";
import type {
  UploadResponse,
  ColumnInfo,
  RolesResponse,
  PaletteListResponse,
  PaletteColorsResponse,
  RenderRequest,
  RenderResponse,
} from "../types";

// ── Upload ──────────────────────────────────────────────────────
export function useUploadFile() {
  return useMutation<UploadResponse, Error, File>({
    mutationFn: async (file) => {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post<UploadResponse>("/upload", form);
      setSessionId(data.session_id);
      return data;
    },
  });
}

// ── Columns ─────────────────────────────────────────────────────
export function useColumns(sessionId: string | null) {
  return useQuery<{ columns: ColumnInfo[] }>({
    queryKey: ["columns", sessionId],
    queryFn: async () => {
      const { data } = await api.get("/columns");
      return data;
    },
    enabled: !!sessionId,
  });
}

export function useSetRoles() {
  return useMutation<RolesResponse, Error, Record<string, string>>({
    mutationFn: async (roles) => {
      const { data } = await api.post<RolesResponse>("/columns/roles", {
        roles,
      });
      return data;
    },
  });
}

// ── Palettes ────────────────────────────────────────────────────
export function usePalettes() {
  return useQuery<PaletteListResponse>({
    queryKey: ["palettes"],
    queryFn: async () => {
      const { data } = await api.get<PaletteListResponse>("/palettes");
      return data;
    },
    staleTime: Infinity,
  });
}

export function usePaletteColors(paletteName: string, n: number) {
  return useQuery<PaletteColorsResponse>({
    queryKey: ["palette-colors", paletteName, n],
    queryFn: async () => {
      const { data } = await api.post<PaletteColorsResponse>(
        "/palette-colors",
        { palette_name: paletteName, n_colors: n }
      );
      return data;
    },
    enabled: !!paletteName && n > 0,
    staleTime: Infinity,
  });
}

// ── Render ──────────────────────────────────────────────────────
export function useRender() {
  return useMutation<RenderResponse, Error, RenderRequest>({
    mutationFn: async (req) => {
      const { data } = await api.post<RenderResponse>("/render", req);
      return data;
    },
  });
}
