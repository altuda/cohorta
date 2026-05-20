import { useEffect, useState } from "react";
import { useSessionStore } from "../../stores/useSessionStore";
import { usePalettes, usePaletteColors } from "../../api/hooks";
import { HexColorPicker } from "react-colorful";

function ColorSwatch({
  color,
  selected,
  onClick,
  label,
}: {
  color: string;
  selected?: boolean;
  onClick: () => void;
  label?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-7 h-7 rounded border-2 text-[10px] font-bold text-white flex items-center justify-center transition-all ${
        selected
          ? "border-slate-800 scale-110 shadow"
          : "border-transparent hover:border-slate-300"
      }`}
      style={{ backgroundColor: color, textShadow: "0 0 2px rgba(0,0,0,.6)" }}
      title={color}
    >
      {label}
    </button>
  );
}

function MutTypeColorPicker({
  mt,
  defaultColor,
}: {
  mt: string;
  defaultColor: string;
}) {
  const color = useSessionStore((s) => s.mutationColors[mt] ?? defaultColor);
  const setMutationColor = useSessionStore((s) => s.setMutationColor);
  const [open, setOpen] = useState(false);

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => setOpen(!open)}
        className="w-6 h-6 rounded border border-slate-200 shrink-0"
        style={{ backgroundColor: color }}
      />
      <span className="text-xs text-slate-700 truncate flex-1">{mt}</span>
      {open && (
        <div className="absolute z-50 mt-2">
          <div
            className="fixed inset-0"
            onClick={() => setOpen(false)}
          />
          <div className="relative bg-white rounded-lg shadow-lg border p-2">
            <HexColorPicker
              color={color}
              onChange={(c) => setMutationColor(mt, c)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default function MutationColorsPanel() {
  const roles = useSessionStore((s) => s.roles);
  const mutationTypes = useSessionStore((s) => s.mutationTypes);
  const mutationColors = useSessionStore((s) => s.mutationColors);
  const setMutationColor = useSessionStore((s) => s.setMutationColor);
  const setMutationColorsBatch = useSessionStore((s) => s.setMutationColorsBatch);

  const hasGene = Object.values(roles).includes("Gene / Feature");
  const { data: palettes } = usePalettes();

  const [palette, setPalette] = useState("tab10");
  const [singleMode, setSingleMode] = useState(false);
  const [singleColor, setSingleColor] = useState("#1f77b4");

  const n = Math.max(mutationTypes.length, 1);
  const { data: paletteColors } = usePaletteColors(palette, n);

  // Apply single color or palette defaults — single batch update
  useEffect(() => {
    if (!paletteColors?.colors || !mutationTypes.length) return;
    const defaults = paletteColors.colors;
    const batch: Record<string, string> = {};
    let changed = false;
    for (let i = 0; i < mutationTypes.length; i++) {
      const mt = mutationTypes[i];
      if (singleMode) {
        batch[mt] = singleColor;
        changed = true;
      } else if (!mutationColors[mt]) {
        batch[mt] = defaults[i % defaults.length];
        changed = true;
      }
    }
    if (changed) setMutationColorsBatch(batch);
  }, [mutationTypes, paletteColors, singleMode, singleColor]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!hasGene) return null;

  const hasMut = Object.values(roles).includes("Mutation Type");
  const heading = hasMut ? "Mutation Type Colours" : "Gene / Alteration Colours";
  const shown = mutationTypes.slice(0, 20);

  return (
    <div>
      <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-2">
        {heading}
      </h2>

      <div className="space-y-2">
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
        {paletteColors?.colors && (
          <div className="flex flex-wrap gap-1">
            {paletteColors.colors.map((c, i) => (
              <div
                key={i}
                className="w-5 h-5 rounded text-[9px] text-white font-bold flex items-center justify-center"
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

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={singleMode}
            onChange={(e) => setSingleMode(e.target.checked)}
          />
          <span className="text-slate-700">Use single colour</span>
        </label>

        {singleMode ? (
          <div className="flex items-center gap-2">
            <input
              type="color"
              value={singleColor}
              onChange={(e) => setSingleColor(e.target.value)}
              className="w-8 h-8 rounded border border-slate-200 cursor-pointer"
            />
            <span className="text-xs text-slate-500">{singleColor}</span>
          </div>
        ) : (
          <div className="space-y-1.5 max-h-80 overflow-y-auto">
            {shown.map((mt) => (
              <MutTypeColorPicker
                key={mt}
                mt={mt}
                defaultColor={
                  paletteColors?.colors[
                    mutationTypes.indexOf(mt) %
                      (paletteColors?.colors.length || 1)
                  ] ?? "#808080"
                }
              />
            ))}
            {mutationTypes.length > 20 && (
              <p className="text-xs text-slate-400">
                Showing 20 of {mutationTypes.length}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
