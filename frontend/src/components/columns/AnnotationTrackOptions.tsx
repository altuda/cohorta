import { useState, useEffect, useMemo } from "react";
import { HexColorPicker } from "react-colorful";
import { useSessionStore } from "../../stores/useSessionStore";
import { usePalettes, usePaletteColors } from "../../api/hooks";
import type { TrackOptionsPayload } from "../../types";

const EMPTY_ARRAY: string[] = [];
const DEFAULT_TRACK_OPTS: TrackOptionsPayload = {
  show_values: false,
  text_color: "#000000",
  tile_color: null,
};

function ColorPopover({
  color,
  onChange,
}: {
  color: string;
  onChange: (c: string) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative inline-block">
      <button
        onClick={() => setOpen(!open)}
        className="w-6 h-6 rounded border border-slate-300 shrink-0"
        style={{ backgroundColor: color }}
      />
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute z-50 left-0 top-8 bg-white rounded-lg shadow-lg border p-2">
            <HexColorPicker color={color} onChange={onChange} />
          </div>
        </>
      )}
    </div>
  );
}

export default function AnnotationTrackOptions({ col }: { col: string }) {
  const annotationType = useSessionStore(
    (s) => s.annotationTypes[col] ?? "Categorical"
  );
  const setAnnotationType = useSessionStore((s) => s.setAnnotationType);
  const annotationColors = useSessionStore((s) => s.annotationColors[col]);
  const setAnnotationColor = useSessionStore((s) => s.setAnnotationColor);
  const trackOptions = useSessionStore(
    (s) => s.trackOptions[col] ?? DEFAULT_TRACK_OPTS
  );
  const setTrackOption = useSessionStore((s) => s.setTrackOption);
  const uniqueValues = useSessionStore(
    (s) => s.annotationUniqueValues[col] ?? EMPTY_ARRAY
  );

  const { data: palettes } = usePalettes();
  const [palette, setPalette] = useState("tab10");
  const [useTileColor, setUseTileColor] = useState(!!trackOptions.tile_color);

  const nPal = 10;
  const { data: paletteColors } = usePaletteColors(palette, nPal);
  const palColors = paletteColors?.colors ?? EMPTY_ARRAY;

  // Memoize the color map to avoid reading stale closures
  const existingColorMap = useMemo(() => {
    if (typeof annotationColors === "object" && annotationColors !== null) {
      return annotationColors as Record<string, string>;
    }
    return {} as Record<string, string>;
  }, [annotationColors]);

  // Initialize categorical colors from palette
  useEffect(() => {
    if (
      annotationType !== "Categorical" ||
      useTileColor ||
      !palColors.length ||
      !uniqueValues.length
    )
      return;

    const needsDefaults = uniqueValues.some((v) => !existingColorMap[v]);
    if (!needsDefaults) return;

    const spread = uniqueValues.map((_, i) =>
      Math.round(
        (i / Math.max(uniqueValues.length - 1, 1)) * (palColors.length - 1)
      )
    );
    const colorMap: Record<string, string> = {};
    uniqueValues.forEach((v, i) => {
      colorMap[v] = existingColorMap[v] ?? palColors[spread[i]] ?? "#808080";
    });
    setAnnotationColor(col, colorMap);
  }, [palColors, uniqueValues, annotationType, useTileColor, existingColorMap, col, setAnnotationColor]);

  return (
    <div className="space-y-2 mt-1">
      <label className="block">
        <span className="text-xs text-slate-500">Type</span>
        <select
          value={annotationType}
          onChange={(e) => setAnnotationType(col, e.target.value)}
          className="mt-0.5 block w-full rounded border border-slate-200 px-2 py-1 text-sm bg-white"
        >
          <option>Categorical</option>
          <option>Continuous</option>
        </select>
      </label>

      {/* Tile color override */}
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={useTileColor}
          onChange={(e) => {
            setUseTileColor(e.target.checked);
            setTrackOption(col, {
              tile_color: e.target.checked ? "#E0E0E0" : null,
            });
            if (e.target.checked) {
              setAnnotationColor(col, {});
            }
          }}
        />
        <span className="text-slate-700">Single tile colour</span>
      </label>

      {useTileColor && (
        <div className="flex items-center gap-2">
          <input
            type="color"
            value={trackOptions.tile_color ?? "#E0E0E0"}
            onChange={(e) =>
              setTrackOption(col, { tile_color: e.target.value })
            }
            className="w-8 h-8 rounded border border-slate-200 cursor-pointer"
          />
          <span className="text-xs text-slate-500">
            {trackOptions.tile_color}
          </span>
        </div>
      )}

      {/* Categorical color assignment */}
      {annotationType === "Categorical" && !useTileColor && (
        <div className="space-y-1.5">
          <label className="block">
            <span className="text-xs text-slate-500">Palette</span>
            <select
              value={palette}
              onChange={(e) => setPalette(e.target.value)}
              className="mt-0.5 block w-full rounded border border-slate-200 px-2 py-1 text-sm bg-white"
            >
              {(palettes?.categorical ?? []).map((p) => (
                <option key={p}>{p}</option>
              ))}
            </select>
          </label>

          {/* Palette swatches */}
          {palColors.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {palColors.map((c, i) => (
                <div
                  key={i}
                  className="w-5 h-5 rounded text-[9px] text-white font-bold flex items-center justify-center cursor-default"
                  style={{
                    backgroundColor: c,
                    textShadow: "0 0 2px rgba(0,0,0,.5)",
                  }}
                >
                  {i + 1}
                </div>
              ))}
            </div>
          )}

          {/* Per-value color assignment */}
          <div className="space-y-1 max-h-60 overflow-y-auto">
            {uniqueValues.slice(0, 15).map((val) => {
              const current = existingColorMap[val] ?? "#808080";
              return (
                <div key={val} className="flex items-center gap-2">
                  <ColorPopover
                    color={current}
                    onChange={(c) => {
                      setAnnotationColor(col, {
                        ...existingColorMap,
                        [val]: c,
                      });
                    }}
                  />
                  <span className="text-xs text-slate-700 truncate">
                    {val}
                  </span>
                  {/* Quick palette picks */}
                  <div className="flex gap-0.5 ml-auto">
                    {palColors.slice(0, 6).map((pc, pi) => (
                      <button
                        key={pi}
                        onClick={() =>
                          setAnnotationColor(col, {
                            ...existingColorMap,
                            [val]: pc,
                          })
                        }
                        className={`w-4 h-4 rounded-sm border ${
                          current === pc
                            ? "border-slate-800"
                            : "border-transparent hover:border-slate-300"
                        }`}
                        style={{ backgroundColor: pc }}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
            {uniqueValues.length > 15 && (
              <p className="text-xs text-slate-400">
                Showing 15 of {uniqueValues.length}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Continuous colormap */}
      {annotationType === "Continuous" && !useTileColor && (
        <label className="block">
          <span className="text-xs text-slate-500">Colormap</span>
          <select
            value={
              typeof annotationColors === "string"
                ? annotationColors
                : "viridis"
            }
            onChange={(e) => setAnnotationColor(col, e.target.value)}
            className="mt-0.5 block w-full rounded border border-slate-200 px-2 py-1 text-sm bg-white"
          >
            {[
              "viridis", "plasma", "inferno", "magma",
              "coolwarm", "RdBu", "YlOrRd", "Blues",
            ].map((cm) => (
              <option key={cm}>{cm}</option>
            ))}
          </select>
        </label>
      )}

      {/* Show values in tiles */}
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={trackOptions.show_values}
          onChange={(e) =>
            setTrackOption(col, { show_values: e.target.checked })
          }
        />
        <span className="text-slate-700">Show values in tiles</span>
      </label>

      {trackOptions.show_values && (
        <div className="flex items-center gap-2">
          <input
            type="color"
            value={trackOptions.text_color}
            onChange={(e) =>
              setTrackOption(col, { text_color: e.target.value })
            }
            className="w-6 h-6 rounded border border-slate-200 cursor-pointer"
          />
          <span className="text-xs text-slate-500">Text colour</span>
        </div>
      )}
    </div>
  );
}
